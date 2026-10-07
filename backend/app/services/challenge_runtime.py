"""Servicios de ejecución: flags dinámicas, sincronización Guacamole y selección de VM."""

from __future__ import annotations

from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..guacamole import GuacamoleApiError
from ..domain.flags.service import FlagService
from ..models import Challenge, ChallengeGroupAssignment, GroupMembership, Laboratory, StudentGroup, User, VMAsset


ESC_ATTACKER_NAME = "LAB-KALI"
ESC_ATTACKER_IP = "192.168.146.134"
ESC_VICTIM_NAME = "LAB-LNXVICT"
ESC_VICTIM_IP = "192.168.146.137"


class EscAttackerNotReady(ValueError):
    """Kali no puede abrirse de forma inequívoca para el jugador."""


def _unique_esc_kali_connections(connections) -> dict[str, str]:
    targets: dict[str, str] = {}
    for protocol in ("ssh", "rdp"):
        matches = [
            connection for connection in connections
            if (connection.protocol or "").strip().lower() == protocol
            and _asset_ref_key(connection.hostname or "") == ESC_ATTACKER_IP
        ]
        if len(matches) == 1:
            targets[protocol] = str(matches[0].identifier)
    return targets


def _esc_sync_connection_ids(challenge: Challenge, vms, labs, connections) -> set[str]:
    refs = challenge.asset_references or []
    if challenge.code != "ESC-01-RECON" or ESC_VICTIM_NAME not in refs or ESC_ATTACKER_NAME not in refs:
        return set()

    def ready_unique_vm(name: str, ip: str) -> bool:
        owners = [vm for vm in vms if _asset_ref_key(vm.ip_address or "") == ip]
        if len(owners) != 1:
            return False
        vm = owners[0]
        return (
            vm.name == name and vm.status == "ready"
            and any(lab.id == vm.laboratory_id and lab.status == "ready" for lab in labs)
        )

    if not ready_unique_vm(ESC_VICTIM_NAME, ESC_VICTIM_IP) or not ready_unique_vm(ESC_ATTACKER_NAME, ESC_ATTACKER_IP):
        return set()
    return set(_unique_esc_kali_connections(connections).values())

def render_dynamic_flag(template: str, *, code: str, username: str, run_id: int) -> str:
    """Compatibilidad con llamadas existentes; el dominio genera la parte aleatoria."""
    return FlagService().render_template(template, code=code, username=username, run_id=run_id)


# ============================================================
# EJECUCIÓN Y VALIDACIÓN DE RETOS
# ============================================================

def _asset_ref_key(value: str) -> str:
    return value.strip().upper()


def _guacamole_access_references(challenge: Challenge) -> list[str]:
    """La VM víctima de ESC se usa para inyección, no para acceso del jugador."""
    refs = challenge.asset_references or []
    if challenge.code == "ESC-01-RECON":
        return [ref for ref in refs if _asset_ref_key(ref) == "LAB-KALI"]
    return refs


async def _resolve_esc_attacker_targets(app, session, username: str, challenge: Challenge,
                                        victim_vm: VMAsset | None) -> dict[str, str]:
    """Comprueba inventario, conexiones y READ directo antes de usar Kali.

    La misma resolución se aplica al inicio y a cada ticket de terminal. Una
    conexión ambigua se omite, aunque el usuario tenga permiso sobre ella.
    """
    if (
        challenge.code != "ESC-01-RECON"
        or ESC_ATTACKER_NAME not in (challenge.asset_references or [])
        or victim_vm is None
        or victim_vm.name != ESC_VICTIM_NAME
        or victim_vm.ip_address != ESC_VICTIM_IP
        or victim_vm.status != "ready"
    ):
        raise EscAttackerNotReady("ESC-01-RECON requiere la VM víctima Linux confirmada y la referencia LAB-KALI")

    attackers = list((await session.scalars(
        select(VMAsset).where(VMAsset.ip_address == ESC_ATTACKER_IP)
    )).all())
    if len(attackers) != 1 or attackers[0].name != ESC_ATTACKER_NAME or attackers[0].status != "ready":
        raise EscAttackerNotReady("Kali debe estar registrada una sola vez y en estado listo")
    attacker_lab = await session.get(Laboratory, attackers[0].laboratory_id)
    if attacker_lab is None or attacker_lab.status != "ready":
        raise EscAttackerNotReady("El laboratorio de Kali debe estar en estado listo")

    try:
        connections = await app.state.guacamole_admin.list_connections()
        permissions = await app.state.guacamole_admin.get_user_permissions(username)
    except Exception as exc:
        raise HTTPException(503, "No se pudo comprobar el acceso a Kali en Guacamole") from exc

    candidates = _unique_esc_kali_connections(connections)
    if not candidates:
        raise EscAttackerNotReady("Kali necesita una conexión SSH o RDP única hacia 192.168.146.134")

    readable = {
        str(identifier) for identifier, values in (permissions.get("connectionPermissions") or {}).items()
        if "READ" in (values or [])
    }
    targets = {protocol: identifier for protocol, identifier in candidates.items() if identifier in readable}
    if not targets:
        raise EscAttackerNotReady("Tu cuenta de laboratorio necesita permiso de lectura sobre la conexión Kali")
    return targets


async def _sync_player_guacamole_permissions(request: Request, user_id: int) -> None:
    """Concede al jugador únicamente las conexiones Guacamole de sus retos asignados.

    Cuando vm_assets.guacamole_connection_id está vacío, resuelve la conexión
    por nombre/IP y protocolo usando los parámetros reales de Guacamole.
    """
    async with request.app.state.session_factory() as session:
        user = await session.get(User, user_id)
        if user is None or user.role != "player":
            return

        assigned_challenges = (
            await session.scalars(
                select(Challenge)
                .join(ChallengeGroupAssignment, ChallengeGroupAssignment.challenge_id == Challenge.id)
                .join(GroupMembership, GroupMembership.group_id == ChallengeGroupAssignment.group_id)
                .join(StudentGroup, StudentGroup.id == GroupMembership.group_id)
                .where(GroupMembership.user_id == user_id, StudentGroup.is_active.is_(True), Challenge.is_published.is_(True))
            )
        ).unique().all()

        vms = (await session.scalars(select(VMAsset))).all()

        try:
            guac_connections = await request.app.state.guacamole_admin.list_connections()
        except GuacamoleApiError as exc:
            raise HTTPException(status_code=502, detail=f"No se pudieron consultar las conexiones de Guacamole: {exc}") from exc

        refs_to_connections: dict[str, str] = {}
        for vm in vms:
            explicit = str(vm.guacamole_connection_id) if vm.guacamole_connection_id else None
            matched = None
            if explicit:
                matched = next((c for c in guac_connections if c.identifier == explicit), None)
            if matched is None and vm.ip_address:
                target_ip = _asset_ref_key(vm.ip_address)
                matched = next(
                    (c for c in guac_connections
                     if _asset_ref_key(c.hostname or "") == target_ip
                     and (c.protocol or "").strip().lower() in {"ssh", "rdp", "vnc"}),
                    None,
                )
            if matched is None:
                continue
            connection_id = str(matched.identifier)
            refs_to_connections[_asset_ref_key(vm.name)] = connection_id
            if vm.ip_address:
                refs_to_connections[_asset_ref_key(vm.ip_address)] = connection_id

        lab_rows = (await session.scalars(select(Laboratory))).all()
        labs_by_key: dict[str, int] = {}
        for lab in lab_rows:
            labs_by_key[_asset_ref_key(lab.name)] = lab.id
            if lab.code:
                labs_by_key[_asset_ref_key(lab.code)] = lab.id

        vm_by_lab: dict[int, list[VMAsset]] = {}
        for vm in vms:
            vm_by_lab.setdefault(vm.laboratory_id, []).append(vm)

        desired: dict[str, list[str]] = {}
        for challenge in assigned_challenges:
            if challenge.code == "ESC-01-RECON":
                for connection_id in _esc_sync_connection_ids(challenge, vms, lab_rows, guac_connections):
                    desired[connection_id] = ["READ"]
                continue
            for raw_ref in _guacamole_access_references(challenge):
                key = _asset_ref_key(raw_ref)
                direct = refs_to_connections.get(key)
                if direct:
                    desired[direct] = ["READ"]
                    continue
                lab_id = labs_by_key.get(key)
                if lab_id:
                    for vm in vm_by_lab.get(lab_id, []):
                        connection_id = refs_to_connections.get(_asset_ref_key(vm.name))
                        if connection_id:
                            desired[connection_id] = ["READ"]

        username = user.username

    try:
        await request.app.state.guacamole_admin.patch_user_permissions(
            username,
            system_permissions=[],
            connection_permissions=desired,
        )
    except GuacamoleApiError as exc:
        if exc.status_code != 404:
            raise HTTPException(status_code=502, detail=f"No se pudieron sincronizar los permisos de Guacamole: {exc.detail or exc}") from exc


async def _sync_guacamole_group_permissions(request: Request, group_id: int) -> None:
    """Sincroniza un grupo académico con sus conexiones reales de Guacamole."""
    async with request.app.state.session_factory() as session:
        group = await session.get(StudentGroup, group_id)
        if group is None:
            return
        if not group.guacamole_group_identifier:
            group.guacamole_group_identifier = group.code
            await session.commit()

        assigned_challenges = (await session.scalars(
            select(Challenge)
            .join(ChallengeGroupAssignment, ChallengeGroupAssignment.challenge_id == Challenge.id)
            .where(ChallengeGroupAssignment.group_id == group_id, Challenge.is_published.is_(True))
        )).unique().all()
        vms = (await session.scalars(select(VMAsset))).all()
        labs = (await session.scalars(select(Laboratory))).all()
        labs_by_key = {_asset_ref_key(l.code): l.id for l in labs if l.code}
        labs_by_key.update({_asset_ref_key(l.name): l.id for l in labs})
        vm_by_lab: dict[int, list[VMAsset]] = {}
        for vm in vms:
            vm_by_lab.setdefault(vm.laboratory_id, []).append(vm)

    try:
        guac_connections = await request.app.state.guacamole_admin.list_connections()
    except GuacamoleApiError as exc:
        raise HTTPException(status_code=502, detail=f"No se pudieron consultar las conexiones de Guacamole: {exc}") from exc

    refs_to_connections: dict[str, str] = {}
    for vm in vms:
        matched = None
        if vm.guacamole_connection_id:
            matched = next((c for c in guac_connections if c.identifier == str(vm.guacamole_connection_id)), None)
        if matched is None and vm.ip_address:
            target_ip = _asset_ref_key(vm.ip_address)
            matched = next(
                (c for c in guac_connections
                 if _asset_ref_key(c.hostname or "") == target_ip
                 and (c.protocol or "").strip().lower() in {"ssh", "rdp", "vnc"}),
                None,
            )
        if matched:
            refs_to_connections[_asset_ref_key(vm.name)] = str(matched.identifier)
            if vm.ip_address:
                refs_to_connections[_asset_ref_key(vm.ip_address)] = str(matched.identifier)

    desired: dict[str, list[str]] = {}
    for challenge in assigned_challenges:
        if challenge.code == "ESC-01-RECON":
            for connection_id in _esc_sync_connection_ids(challenge, vms, labs, guac_connections):
                desired[connection_id] = ["READ"]
            continue
        for raw_ref in _guacamole_access_references(challenge):
            key = _asset_ref_key(raw_ref)
            direct = refs_to_connections.get(key)
            if direct:
                desired[direct] = ["READ"]
                continue
            lab_id = labs_by_key.get(key)
            if lab_id:
                for vm in vm_by_lab.get(lab_id, []):
                    connection_id = refs_to_connections.get(_asset_ref_key(vm.name))
                    if connection_id:
                        desired[connection_id] = ["READ"]

    guac_identifier = group.guacamole_group_identifier
    try:
        try:
            await request.app.state.guacamole_admin.get_user_group_permissions(guac_identifier)
        except GuacamoleApiError as exc:
            if exc.status_code == 404:
                await request.app.state.guacamole_admin.create_user_group(guac_identifier, disabled=False)
            else:
                raise
        await request.app.state.guacamole_admin.patch_user_group_permissions(guac_identifier, connection_permissions=desired)
    except GuacamoleApiError as exc:
        raise HTTPException(status_code=502, detail=f"No se pudieron sincronizar permisos del grupo con Guacamole: {exc.detail or exc}") from exc


async def _sync_group_members_guacamole_permissions(request: Request, group_id: int) -> None:
    async with request.app.state.session_factory() as session:
        user_ids = list((await session.scalars(select(GroupMembership.user_id).where(GroupMembership.group_id == group_id))).all())
    first_error: Exception | None = None
    for user_id in user_ids:
        try:
            await _sync_player_guacamole_permissions(request, int(user_id))
        except Exception as exc:
            if first_error is None:
                first_error = exc
    if first_error is not None:
        raise first_error


async def _reconcile_esc_guacamole_access(request: Request, group_ids: list[int]) -> None:
    """Intenta reconciliar grupos y usuarios, aun si una escritura remota falla."""
    first_error: Exception | None = None
    for group_id in group_ids:
        for sync in (_sync_guacamole_group_permissions, _sync_group_members_guacamole_permissions):
            try:
                await sync(request, group_id)
            except Exception as exc:
                if first_error is None:
                    first_error = exc
    if first_error is not None:
        raise first_error


async def _find_challenge_vm(session, challenge: Challenge):
    """Busca la VM víctima sin exigir que su conexión Guacamole esté escrita en PostgreSQL."""
    refs = [_asset_ref_key(value) for value in (challenge.asset_references or []) if value.strip()]

    labs = (
        await session.scalars(
            select(Laboratory)
            .options(selectinload(Laboratory.vms))
            .where(Laboratory.status.in_(("ready", "planned")))
            .order_by(Laboratory.id)
        )
    ).unique().all()

    # LAB-01 tiene un destino físico confirmado. Un inventario legado puede
    # contener otra ficha con la misma IP (p. ej. una Kali etiquetada como
    # víctima); nunca debe elegirse por coincidencia de IP o código del lab.
    if challenge.code == "LAB-01":
        matches = [
            (lab, vm) for lab in labs if lab.status == "ready" for vm in lab.vms
            if vm.status == "ready"
            and _asset_ref_key(vm.name) == "LAB-LNXVICT"
            and _asset_ref_key(vm.ip_address or "") == "192.168.146.137"
            and ("linux" in vm.os.lower() or "ubuntu" in vm.os.lower())
        ]
        return matches[0] if len(matches) == 1 else (None, None)

    ready_vms = [
        (lab, vm) for lab in labs if lab.status == "ready"
        for vm in lab.vms if vm.status == "ready"
    ]

    def unique_target(matches):
        if len(matches) != 1:
            return None, None
        selected_lab, selected_vm = matches[0]
        # Even an exact VM name is unsafe if a stale inventory row names the
        # same physical IP. Unlike LAB-01, no generic challenge has a trusted
        # fixed target that can disambiguate this situation.
        if selected_vm.ip_address:
            owners = [
                vm for lab in labs for vm in lab.vms
                if _asset_ref_key(vm.ip_address or "") == _asset_ref_key(selected_vm.ip_address)
            ]
            if len(owners) != 1:
                return None, None
        return selected_lab, selected_vm

    # The first resolvable reference is the target. Direct VM references take
    # precedence over laboratory labels for that reference only; never turn all
    # references into a set, since that can redirect injection to an attacker.
    for ref in refs:
        direct = [
            (lab, vm) for lab, vm in ready_vms
            if ref in {_asset_ref_key(vm.name), _asset_ref_key(vm.ip_address or "")}
        ]
        if direct:
            return unique_target(direct)

        matching_labs = [
            lab for lab in labs if lab.status == "ready"
            and ref in {_asset_ref_key(lab.code or ""), _asset_ref_key(lab.name)}
        ]
        if matching_labs:
            if len(matching_labs) != 1:
                return None, None
            return unique_target([(lab, vm) for lab, vm in ready_vms if lab is matching_labs[0]])

    return None, None


async def _resolve_guacamole_connection(request: Request, vm: VMAsset):
    """Obtiene la conexión SSH de Guacamole por IP cuando vm_assets no guarda el ID."""
    if vm.guacamole_connection_id:
        return next(
            (item for item in await request.app.state.guacamole_admin.list_connections()
             if item.identifier == vm.guacamole_connection_id),
            None,
        )

    try:
        connections = await request.app.state.guacamole_admin.list_connections()
    except GuacamoleApiError:
        return None

    target_ip = _asset_ref_key(vm.ip_address or "")
    for connection in connections:
        host = _asset_ref_key(connection.hostname or "")
        protocol = (connection.protocol or "").strip().lower()
        if host == target_ip and protocol == "ssh":
            return connection
    return None
