# ============================================================
# ADAPTADORES DE GUACAMOLE
# Responsabilidad: encapsular autenticación HTTP, usuarios, conexiones y permisos de Guacamole.
# ============================================================

from __future__ import annotations

import asyncio
import base64
import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from .core import get_settings


@dataclass(frozen=True)
class RemoteConnection:
    external_reference: str
    launch_url: str


@dataclass(frozen=True)
class GuacamoleUser:
    username: str
    attributes: dict
    last_active: int | None = None


@dataclass(frozen=True)
class GuacamoleConnection:
    identifier: str
    name: str
    protocol: str
    parent_identifier: str = "ROOT"
    hostname: str | None = None
    port: str | None = None
    parameters: dict | None = None
    attributes: dict | None = None
    active_connections: int = 0


class GuacamoleApiError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None, detail: str | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail


class RemoteAccessProvisioningPort:
    async def provision(self, username: str, challenge_code: str, run_id: int) -> RemoteConnection:
        raise NotImplementedError
    async def revoke(self, external_reference: str) -> None:
        raise NotImplementedError


class GuacamoleAdminPort:
    async def list_users(self) -> list[GuacamoleUser]: raise NotImplementedError
    async def list_user_groups(self) -> list[dict]: raise NotImplementedError
    async def create_user_group(self, identifier: str, *, disabled: bool = False) -> dict: raise NotImplementedError
    async def update_user_group(self, identifier: str, *, disabled: bool = False) -> dict: raise NotImplementedError
    async def delete_user_group(self, identifier: str) -> None: raise NotImplementedError
    async def add_user_group_member(self, identifier: str, username: str) -> None: raise NotImplementedError
    async def remove_user_group_member(self, identifier: str, username: str) -> None: raise NotImplementedError
    async def get_user_group_permissions(self, identifier: str) -> dict: raise NotImplementedError
    async def patch_user_group_permissions(self, identifier: str, *, connection_permissions: dict[str, list[str]]) -> dict: raise NotImplementedError
    async def create_user(self, username: str, password: str, *, email: str | None = None, full_name: str | None = None) -> GuacamoleUser: raise NotImplementedError
    async def update_user(self, username: str, *, password: str | None = None, email: str | None = None, full_name: str | None = None, disabled: bool | None = None) -> GuacamoleUser: raise NotImplementedError
    async def delete_user(self, username: str) -> None: raise NotImplementedError
    async def list_connections(self) -> list[GuacamoleConnection]: raise NotImplementedError
    async def create_connection(self, *, name: str, protocol: str, hostname: str, port: int, username: str | None = None, password: str | None = None, domain: str | None = None, parent_identifier: str = "ROOT") -> GuacamoleConnection: raise NotImplementedError
    async def update_connection(self, identifier: str, *, name: str, protocol: str, hostname: str, port: int, username: str | None = None, password: str | None = None, domain: str | None = None, parent_identifier: str = "ROOT") -> GuacamoleConnection: raise NotImplementedError
    async def delete_connection(self, identifier: str) -> None: raise NotImplementedError
    async def get_user_permissions(self, username: str) -> dict: raise NotImplementedError
    async def patch_user_permissions(self, username: str, *, system_permissions: list[str], connection_permissions: dict[str, list[str]]) -> dict: raise NotImplementedError
    async def status(self) -> dict: raise NotImplementedError


class StubGuacamoleAdapter(RemoteAccessProvisioningPort, GuacamoleAdminPort):
    def __init__(self) -> None:
        self.users: dict[str, GuacamoleUser] = {"guacadmin": GuacamoleUser("guacadmin", {})}
        self.connections: dict[str, GuacamoleConnection] = {}
        self.permissions: dict[str, dict] = {"guacadmin": {"systemPermissions": ["ADMINISTER"], "connectionPermissions": {}}}
        self._next_connection = 1

    async def provision(self, username: str, challenge_code: str, run_id: int) -> RemoteConnection:
        settings = get_settings(); ref = f"ctf-{username}-{challenge_code.lower()}-{run_id}"
        return RemoteConnection(ref, f"{settings.guacamole_base_url.rstrip('/')}/#/home")
    async def revoke(self, external_reference: str) -> None: return None
    async def direct_connection_url(self, identifier: str) -> str:
        settings=get_settings()
        return f"{settings.guacamole_base_url.rstrip('/')}/#/client/{identifier}"
    async def list_users(self) -> list[GuacamoleUser]: return list(self.users.values())
    async def list_user_groups(self) -> list[dict]:
        return [{"identifier": key, "attributes": {}, "disabled": False, "memberUsers": []} for key in self.permissions.get("__groups__", {}).keys()]
    async def create_user_group(self, identifier: str, *, disabled: bool = False) -> dict:
        groups = self.permissions.setdefault("__groups__", {})
        if identifier in groups: raise GuacamoleApiError("El grupo ya existe en Guacamole", 409)
        groups[identifier] = {"disabled": disabled, "members": set(), "connectionPermissions": {}}
        return {"identifier": identifier, "attributes": {}, "disabled": disabled}
    async def update_user_group(self, identifier: str, *, disabled: bool = False) -> dict:
        groups = self.permissions.setdefault("__groups__", {})
        if identifier not in groups: raise GuacamoleApiError("Grupo no encontrado", 404)
        groups[identifier]["disabled"] = disabled
        return {"identifier": identifier, "attributes": {}, "disabled": disabled}
    async def delete_user_group(self, identifier: str) -> None:
        groups = self.permissions.setdefault("__groups__", {})
        groups.pop(identifier, None)
    async def add_user_group_member(self, identifier: str, username: str) -> None:
        groups = self.permissions.setdefault("__groups__", {})
        if identifier not in groups: raise GuacamoleApiError("Grupo no encontrado", 404)
        groups[identifier]["members"].add(username)
    async def remove_user_group_member(self, identifier: str, username: str) -> None:
        groups = self.permissions.setdefault("__groups__", {})
        if identifier in groups: groups[identifier]["members"].discard(username)
    async def get_user_group_permissions(self, identifier: str) -> dict:
        groups = self.permissions.setdefault("__groups__", {})
        if identifier not in groups: raise GuacamoleApiError("Grupo no encontrado", 404)
        return {"connectionPermissions": groups[identifier].get("connectionPermissions", {})}
    async def patch_user_group_permissions(self, identifier: str, *, connection_permissions: dict[str, list[str]]) -> dict:
        groups = self.permissions.setdefault("__groups__", {})
        if identifier not in groups: raise GuacamoleApiError("Grupo no encontrado", 404)
        groups[identifier]["connectionPermissions"] = connection_permissions
        return {"connectionPermissions": connection_permissions}
    async def create_user(self, username: str, password: str, *, email=None, full_name=None) -> GuacamoleUser:
        if username in self.users: raise GuacamoleApiError("El usuario ya existe", 409)
        user=GuacamoleUser(username,{"guac-email-address":email,"guac-full-name":full_name,"disabled":None}); self.users[username]=user; self.permissions[username] = {"systemPermissions": [], "connectionPermissions": {}}; return user
    async def update_user(self, username: str, *, password=None, email=None, full_name=None, disabled=None) -> GuacamoleUser:
        if username not in self.users: raise GuacamoleApiError("Usuario no encontrado",404)
        a=dict(self.users[username].attributes); 
        if email is not None: a["guac-email-address"]=email
        if full_name is not None: a["guac-full-name"]=full_name
        if disabled is not None: a["disabled"]="true" if disabled else None
        user=GuacamoleUser(username,a); self.users[username]=user; return user
    async def delete_user(self, username: str) -> None:
        if username == "guacadmin": raise GuacamoleApiError("No puedes eliminar guacadmin",409)
        self.users.pop(username,None); self.permissions.pop(username,None)
    async def list_connections(self) -> list[GuacamoleConnection]: return list(self.connections.values())
    async def create_connection(self, *, name, protocol, hostname, port, username=None, password=None, domain=None, parent_identifier="ROOT"):
        ident=str(self._next_connection); self._next_connection+=1; params={"hostname":hostname,"port":str(port)}
        if username is not None: params["username"]=username
        if password is not None: params["password"]=password
        if domain is not None: params["domain"]=domain
        c=GuacamoleConnection(ident,name,protocol,parent_identifier,str(hostname),str(port),params,{},{0}); self.connections[ident]=c; return c
    async def update_connection(self, identifier: str, *, name, protocol, hostname, port, username=None, password=None, domain=None, parent_identifier="ROOT"):
        if identifier not in self.connections: raise GuacamoleApiError("Conexión no encontrada",404)
        old=self.connections[identifier]; params=dict(old.parameters or {}); params.update({"hostname":hostname,"port":str(port)})
        if username is not None: params["username"]=username
        if password is not None: params["password"]=password
        if domain is not None: params["domain"]=domain
        c=GuacamoleConnection(identifier,name,protocol,parent_identifier,hostname,str(port),params,old.attributes or {},old.active_connections); self.connections[identifier]=c; return c
    async def delete_connection(self, identifier: str) -> None: self.connections.pop(identifier,None)
    async def get_user_permissions(self, username: str) -> dict:
        return self.permissions.get(username,{"systemPermissions":[],"connectionPermissions":{}})
    async def patch_user_permissions(self, username: str, *, system_permissions, connection_permissions) -> dict:
        if username not in self.users: raise GuacamoleApiError("Usuario no encontrado",404)
        self.permissions[username]={"systemPermissions":system_permissions,"connectionPermissions":connection_permissions}; return self.permissions[username]
    async def status(self) -> dict:
        s=get_settings(); return {"mode":"stub","connected":True,"base_url":s.guacamole_base_url,"data_source":"stub","username":s.guacamole_service_account or "stub","user_count":len(self.users)}


class ManagedGuacamoleAdapter(RemoteAccessProvisioningPort, GuacamoleAdminPort):
    def __init__(self) -> None:
        s=get_settings(); self.base_url=(s.guacamole_api_url or s.guacamole_base_url).rstrip('/'); self.service_account=s.guacamole_service_account; self.service_password=s.guacamole_service_password
        if not self.service_account or not self.service_password: raise RuntimeError("GUACAMOLE_SERVICE_ACCOUNT y GUACAMOLE_SERVICE_PASSWORD son obligatorios en modo real")
    async def _blocking_request(self, request: Request) -> tuple[int, bytes]:
        def do():
            try:
                with urlopen(request, timeout=15) as response: return int(response.status), response.read()
            except HTTPError as exc:
                body=exc.read().decode('utf-8','ignore'); raise GuacamoleApiError(f"Guacamole respondió HTTP {exc.code}",exc.code,body[:2000]) from exc
            except URLError as exc: raise GuacamoleApiError(f"No se pudo contactar con Guacamole: {exc.reason}") from exc
        return await asyncio.to_thread(do)
    async def _post_token(self):
        body=urlencode({"username":self.service_account,"password":self.service_password}).encode(); req=Request(f"{self.base_url}/api/tokens",data=body,method='POST',headers={"Content-Type":"application/x-www-form-urlencoded"}); _,raw=await self._blocking_request(req); payload=json.loads(raw.decode()); token=payload.get('authToken'); ds=payload.get('dataSource')
        if not token or not ds: raise GuacamoleApiError('Guacamole no devolvió authToken/dataSource')
        return token,ds
    async def _api_request(self, method: str, path: str, *, data: dict | list | None = None):
        token,ds=await self._post_token(); sep='&' if '?' in path else '?'; url=f"{self.base_url}/api/session/data/{quote(ds,safe='')}{path}{sep}token={quote(token,safe='')}"; body=None; headers={"Accept":"application/json"}
        if data is not None: body=json.dumps(data).encode(); headers['Content-Type']='application/json'
        req=Request(url,data=body,method=method,headers=headers); _,raw=await self._blocking_request(req); return json.loads(raw.decode()) if raw else None
    @staticmethod
    def _user(payload): return GuacamoleUser(str(payload.get('username','')),dict(payload.get('attributes') or {}),payload.get('lastActive'))
    @staticmethod
    def _conn(identifier,p):
        params=dict(p.get('parameters') or {}); attrs=dict(p.get('attributes') or {}); return GuacamoleConnection(str(identifier),str(p.get('name','')),str(p.get('protocol','')),str(p.get('parentIdentifier') or 'ROOT'),params.get('hostname'),params.get('port'),params,attrs,int(p.get('activeConnections') or 0))
    async def status(self):
        users=await self.list_users(); token,ds=await self._post_token(); _=token; return {"mode":"real","connected":True,"base_url":self.base_url,"data_source":ds,"username":self.service_account,"user_count":len(users)}
    async def list_users(self):
        p=await self._api_request('GET','/users'); return [self._user(x) for x in p.values()] if isinstance(p,dict) else []
    async def create_user(self,username,password,*,email=None,full_name=None):
        a={"guac-email-address":email,"guac-full-name":full_name,"expired":None,"disabled":None,"timezone":None,"valid-from":None,"valid-until":None,"access-window-start":None,"access-window-end":None,"guac-organization":None,"guac-organizational-role":None}; p=await self._api_request('POST','/users',data={"username":username,"password":password,"attributes":a}); return self._user(p if isinstance(p,dict) else {"username":username,"attributes":a})
    async def update_user(self,username,*,password=None,email=None,full_name=None,disabled=None):
        users=await self._api_request('GET','/users');
        if not isinstance(users,dict) or username not in users: raise GuacamoleApiError(f"El usuario de Guacamole '{username}' no existe",404)
        current=dict(users[username]); current['username']=username; attrs=dict(current.get('attributes') or {}); 
        if email is not None: attrs['guac-email-address']=email
        if full_name is not None: attrs['guac-full-name']=full_name
        if disabled is not None: attrs['disabled']='true' if disabled else None
        current['attributes']=attrs
        if password is not None: current['password']=password
        p=await self._api_request('PUT',f"/users/{quote(username,safe='')}",data=current); return self._user(p if isinstance(p,dict) else current)
    async def delete_user(self,username): await self._api_request('DELETE',f"/users/{quote(username,safe='')}")
    async def list_user_groups(self):
        p = await self._api_request('GET', '/userGroups')
        rows = p.values() if isinstance(p, dict) else []
        return [dict(x) for x in rows if isinstance(x, dict)]
    async def create_user_group(self, identifier: str, *, disabled: bool = False):
        payload = {"identifier": identifier, "attributes": {}, "disabled": bool(disabled)}
        p = await self._api_request('POST', '/userGroups', data=payload)
        return dict(p or payload)
    async def update_user_group(self, identifier: str, *, disabled: bool = False):
        payload = {"identifier": identifier, "attributes": {}, "disabled": bool(disabled)}
        p = await self._api_request('PUT', f'/userGroups/{quote(identifier, safe="")}', data=payload)
        return dict(p or payload)
    async def delete_user_group(self, identifier: str):
        await self._api_request('DELETE', f'/userGroups/{quote(identifier, safe="")}')
    async def add_user_group_member(self, identifier: str, username: str):
        await self._api_request('PATCH', f'/userGroups/{quote(identifier, safe="")}/memberUsers', data=[{"op":"add","path":"/","value":username}])
    async def remove_user_group_member(self, identifier: str, username: str):
        await self._api_request('PATCH', f'/userGroups/{quote(identifier, safe="")}/memberUsers', data=[{"op":"remove","path":"/","value":username}])
    async def get_user_group_permissions(self, identifier: str):
        p = await self._api_request('GET', f'/userGroups/{quote(identifier, safe="")}/permissions')
        if not isinstance(p, dict): return {"connectionPermissions": {}}
        cp = p.get('connectionPermissions') or {}
        if isinstance(cp, list): cp = {str(x): [] for x in cp}
        return {"connectionPermissions": {str(k): list(v or []) for k,v in cp.items()}}
    async def patch_user_group_permissions(self, identifier: str, *, connection_permissions: dict[str, list[str]]):
        current = await self.get_user_group_permissions(identifier)
        old = current.get('connectionPermissions', {})
        ops=[]
        for cid in set(old)|set(connection_permissions):
            oldp=set(old.get(cid,[])); newp=set(connection_permissions.get(cid,[]))
            for perm in sorted(oldp-newp): ops.append({"op":"remove","path":f"/connectionPermissions/{quote(str(cid),safe='')}","value":perm})
            for perm in sorted(newp-oldp): ops.append({"op":"add","path":f"/connectionPermissions/{quote(str(cid),safe='')}","value":perm})
        if ops: await self._api_request('PATCH', f'/userGroups/{quote(identifier, safe="")}/permissions', data=ops)
        return await self.get_user_group_permissions(identifier)
    async def list_connections(self):
        p=await self._api_request('GET','/connections'); return [self._conn(k,v) for k,v in (p or {}).items()] if isinstance(p,dict) else []
    async def create_connection(self,*,name,protocol,hostname,port,username=None,password=None,domain=None,parent_identifier='ROOT'):
        params={"hostname":hostname,"port":str(port)}; 
        if username is not None: params['username']=username
        if password is not None: params['password']=password
        if domain is not None: params['domain']=domain
        p=await self._api_request('POST','/connections',data={"parentIdentifier":parent_identifier,"name":name,"protocol":protocol,"parameters":params,"attributes":{}}); return self._conn((p or {}).get('identifier',''),p or {"name":name,"protocol":protocol,"parameters":params,"attributes":{}})
    async def update_connection(self,identifier,*,name,protocol,hostname,port,username=None,password=None,domain=None,parent_identifier='ROOT'):
        p=await self._api_request('GET',f'/connections/{quote(identifier,safe="")}');
        if not isinstance(p,dict): raise GuacamoleApiError('Conexión no encontrada',404)
        params=dict(p.get('parameters') or {}); params.update({"hostname":hostname,"port":str(port)})
        if username is not None: params['username']=username
        if password is not None: params['password']=password
        if domain is not None: params['domain']=domain
        body={"parentIdentifier":parent_identifier,"name":name,"protocol":protocol,"identifier":identifier,"activeConnections":p.get('activeConnections',0),"parameters":params,"attributes":dict(p.get('attributes') or {})}; await self._api_request('PUT',f'/connections/{quote(identifier,safe="")}',data=body); return self._conn(identifier,body)
    async def delete_connection(self,identifier): await self._api_request('DELETE',f'/connections/{quote(identifier,safe="")}')
    async def get_user_permissions(self,username):
        p=await self._api_request('GET',f'/users/{quote(username,safe="")}/permissions');
        if not isinstance(p,dict): return {"systemPermissions":[],"connectionPermissions":{}}
        cp=p.get('connectionPermissions') or {}; 
        if isinstance(cp,list): cp={str(x):[] for x in cp}
        return {"systemPermissions":list(p.get('systemPermissions') or []),"connectionPermissions":{str(k):list(v or []) for k,v in cp.items()}}
    async def patch_user_permissions(self,username,*,system_permissions,connection_permissions):
        current=await self.get_user_permissions(username); ops=[]
        for perm in sorted(set(current['systemPermissions'])-set(system_permissions)): ops.append({"op":"remove","path":"/systemPermissions","value":perm})
        for perm in sorted(set(system_permissions)-set(current['systemPermissions'])): ops.append({"op":"add","path":"/systemPermissions","value":perm})
        keys=set(current['connectionPermissions'])|set(connection_permissions)
        for cid in keys:
            old=set(current['connectionPermissions'].get(cid,[])); new=set(connection_permissions.get(cid,[]));
            for perm in sorted(old-new): ops.append({"op":"remove","path":f"/connectionPermissions/{quote(str(cid),safe='')}","value":perm})
            for perm in sorted(new-old): ops.append({"op":"add","path":f"/connectionPermissions/{quote(str(cid),safe='')}","value":perm})
        if ops: await self._api_request('PATCH',f'/users/{quote(username,safe="")}/permissions',data=ops)
        return await self.get_user_permissions(username)
    async def provision(self,username,challenge_code,run_id):
        settings=get_settings(); ref=f"ctf-{username}-{challenge_code.lower()}-{run_id}"; return RemoteConnection(ref,f"{settings.guacamole_base_url.rstrip('/')}/#/home")
    async def revoke(self,external_reference): return None
    async def direct_connection_url(self, identifier: str) -> str:
        _, data_source = await self._post_token()
        opaque = base64.b64encode(f"{identifier}\x00c\x00{data_source}".encode()).decode()
        return f"{self.base_url}/#/client/{opaque}"


def make_guacamole_adapter(): return StubGuacamoleAdapter() if get_settings().guacamole_mode.lower()=='stub' else ManagedGuacamoleAdapter()
def make_guacamole_admin(): return StubGuacamoleAdapter() if get_settings().guacamole_mode.lower()=='stub' else ManagedGuacamoleAdapter()
