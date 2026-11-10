"""Contrato HTTP nuevo: permisos, destinos y límites de secretos (sin Guacamole real)."""
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4
import httpx
from fastapi import FastAPI, Request
from app.guacamole import GuacamoleConnection, GuacamoleUser, GuacamoleApiError
from ctf.adapters.http import guacamole_admin as module
from ctf.adapters.http.auth import current


class GuacamoleAdminTests(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.connection = GuacamoleConnection('7', 'Kali Blue SSH', 'ssh', hostname='10.10.20.12', port='22',
                                             parameters={'username':'labops','password':'never-public','private-key':'never-key'}, parent_identifier='group-a')
        self.remote = SimpleNamespace(
            list_connections=AsyncMock(return_value=[self.connection]),
            list_users=AsyncMock(return_value=[GuacamoleUser('operator', {'password':'never-user-secret'}),GuacamoleUser('service',{})]),
            create_connection=AsyncMock(return_value=self.connection), update_connection=AsyncMock(return_value=self.connection),
            delete_connection=AsyncMock(),create_user=AsyncMock(),
            get_user_permissions=AsyncMock(return_value={'systemPermissions':[], 'connectionPermissions':{}}),
            patch_user_permissions=AsyncMock())
        self.audit = Mock()
        @asynccontextmanager
        async def transaction(): yield SimpleNamespace(add=self.audit)
        self.app = FastAPI()
        self.app.include_router(module.router)
        self.app.state.runtime = SimpleNamespace(guacamole=self.remote,settings=SimpleNamespace(guacamole_admin_user='service'),repo=SimpleNamespace(sessions=SimpleNamespace(begin=transaction)))
        self.role=1
        async def identity(request:Request):
            request.state.user_id=uuid4()
            return SimpleNamespace(role=self.role)
        self.app.dependency_overrides[current]=identity
        self.client=httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app),base_url='http://localhost')
        self.base='/api/v1/admin/guacamole'
        self.body={'name':'New Kali SSH','hostname':'10.10.20.12','protocol':'ssh','port':22,'password':'private-credential'}

    async def asyncTearDown(self): await self.client.aclose()

    async def test_requires_admin_and_authentication(self):
        for role in (2,3,4):
            self.role=role
            self.assertEqual((await self.client.get(self.base+'/inventory')).status_code,403)
            self.assertEqual((await self.client.post(self.base+'/connections',json=self.body)).status_code,403)
        self.app.dependency_overrides.clear()
        self.assertEqual((await self.client.get(self.base+'/inventory')).status_code,401)
        self.remote.list_connections.assert_not_awaited()

    async def test_inventory_excludes_secrets_and_protects_service(self):
        response=await self.client.get(self.base+'/inventory')
        self.assertEqual(response.status_code,200)
        self.assertNotIn('never-',response.text)
        self.assertNotIn('parameters',response.text)
        self.assertTrue(response.json()['users'][1]['protected'])

    async def test_external_destination_or_port_never_reaches_adapter(self):
        for changes in ({'hostname':'10.10.10.14'},{'hostname':'example.com'},{'hostname':'127.0.0.1'},{'port':5432},{'protocol':'vnc'}):
            response=await self.client.post(self.base+'/connections',json={**self.body,**changes})
            self.assertEqual(response.status_code,422)
        self.remote.create_connection.assert_not_awaited()

    async def test_create_passes_secret_only_to_adapter(self):
        response=await self.client.post(self.base+'/connections',json=self.body)
        self.assertEqual(response.status_code,201)
        self.assertEqual(self.remote.create_connection.call_args.kwargs['password'],'private-credential')
        self.assertNotIn('private-credential',response.text)
        self.assertNotIn('private-credential',repr(self.audit.call_args))

    async def test_duplicate_name_prevents_creation(self):
        response=await self.client.post(self.base+'/connections',json={**self.body,'name':'kali blue ssh'})
        self.assertEqual(response.status_code,409)
        self.remote.create_connection.assert_not_awaited()

    async def test_update_preserves_password_and_parent(self):
        response=await self.client.put(self.base+'/connections/7',json={**self.body,'password':''})
        self.assertEqual(response.status_code,200)
        self.assertIsNone(self.remote.update_connection.call_args.kwargs['password'])
        self.assertEqual(self.remote.update_connection.call_args.kwargs['parent_identifier'],'group-a')

    async def test_active_and_run_connections_cannot_be_modified(self):
        for changes in ({'active_connections':1},{'name':'ctf_aabbccddeeff'}):
            from dataclasses import replace
            self.remote.list_connections.return_value=[replace(self.connection,**changes)]
            self.assertEqual((await self.client.put(self.base+'/connections/7',json=self.body)).status_code,409)
            self.assertEqual((await self.client.request('DELETE',self.base+'/connections/7',json={'confirmation':'Kali Blue SSH'})).status_code,409)
        self.remote.update_connection.assert_not_awaited()
        self.remote.delete_connection.assert_not_awaited()

    async def test_delete_needs_exact_confirmation(self):
        response=await self.client.request('DELETE',self.base+'/connections/7',json={'confirmation':'wrong'})
        self.assertEqual(response.status_code,422)
        self.remote.delete_connection.assert_not_awaited()
        self.assertEqual((await self.client.request('DELETE',self.base+'/connections/7',json={'confirmation':'Kali Blue SSH'})).status_code,200)

    async def test_test_is_only_tcp_and_never_changes_machine(self):
        with patch.object(module,'check_connection',AsyncMock(return_value={'reachable':True,'message':'Solo TCP'})) as probe:
            response=await self.client.post(self.base+'/connections/7/check')
            self.assertTrue(response.json()['reachable'])
            probe.assert_awaited_once_with(self.connection)
        self.assertEqual(self.audit.call_args.args[0].action,'guacamole.connection.checked')

    async def test_remote_errors_do_not_expose_tokens(self):
        self.remote.list_connections.side_effect=GuacamoleApiError('secret-token',500,detail='password=secret')
        response=await self.client.get(self.base+'/inventory')
        self.assertEqual(response.status_code,502)
        self.assertNotIn('secret',response.text)

    async def test_protected_accounts_and_reserved_names(self):
        for name in ('service','ctf_aabbccddeeff'):
            self.assertEqual((await self.client.get(self.base+f'/users/{name}/access')).status_code,409)
            self.assertEqual((await self.client.post(self.base+'/users',json={'username':name,'password':'valid-test-password'})).status_code,409)
        self.assertEqual((await self.client.post(self.base+'/connections',json={**self.body,'name':'ctf_reserved'})).status_code,422)
        self.remote.create_user.assert_not_awaited()

    async def test_access_update_preserves_unrelated_permissions(self):
        self.remote.get_user_permissions.return_value={'systemPermissions':['CREATE_USER'],'connectionPermissions':{'7':['UPDATE'],'outside':['READ']}}
        response=await self.client.put(self.base+'/users/operator/access',json={'connections':['7']})
        self.assertEqual(response.status_code,200)
        args=self.remote.patch_user_permissions.call_args.kwargs
        self.assertEqual(args['system_permissions'],['CREATE_USER'])
        self.assertEqual(args['connection_permissions'],{'7':['UPDATE','READ'],'outside':['READ']})
        response=await self.client.put(self.base+'/users/operator/access',json={'connections':['outside']})
        self.assertEqual(response.status_code,422)

    async def test_global_admin_permissions_cannot_be_changed(self):
        self.remote.get_user_permissions.return_value={'systemPermissions':['ADMINISTER'],'connectionPermissions':{}}
        self.assertEqual((await self.client.put(self.base+'/users/operator/access',json={'connections':[]})).status_code,409)
        self.remote.patch_user_permissions.assert_not_awaited()
