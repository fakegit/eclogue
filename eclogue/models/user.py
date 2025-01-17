import time
from bson import ObjectId
from eclogue.model import Model, db
from eclogue.models.role import Role
from eclogue.models.menu import Menu
from eclogue.models.group import Group
from eclogue.models.host import Host
from werkzeug.security import generate_password_hash


class User(Model):
    name = 'users'

    def get_permissions(self, user_id, filter=None):
        """
        get user permissions
        :param user_id: user id
        :return: list
        """
        user = self.find_by_id(user_id)
        if not user:
            return []

        relate_team = Model.build_model('team_members').find({'user_id': user_id})
        relate_team = list(relate_team)
        team_ids = list(map(lambda i: i.get('team_id'), relate_team))
        role_ids = []
        menus = []
        if team_ids:
            team_roles = Model.build_model('team_roles').find({'team_id': {'$in': team_ids}})
            for item in team_roles:
                role_ids.append(item.get('role_id'))

        roles = db.collection('user_roles').find({'user_id': user_id})
        roles = list(roles)
        if roles:
            ids = map(lambda i: i['role_id'], roles)
            role_ids += list(ids)

        if role_ids:
            where = {
                'role_id': {
                    '$in': role_ids
                }
            }
            records = db.collection('role_menus').find(where).sort('id', 1)

            for record in records:
                where = filter or {}
                where['_id'] = ObjectId(record['m_id'])
                item = Menu.find_one(where)
                if not item or item.get('mpid') == '-1' or item.get('status') < 1:
                    continue

                item['actions'] = record.get('actions', ['get'])
                menus.append(item)

        roles = Role().find_by_ids(role_ids)

        return menus, roles

    def get_hosts(self, user_id):
        where = {
            'user_id': user_id,
        }
        relations = db.collection('user_hosts').find(where)
        group_ids = []
        host_ids = []
        for item in relations:
            if item.get('type') == 'group':
                group_ids.append(item.get('group_id'))
            else:
                host_ids.append(item.get('host_id'))
        data = {}
        if group_ids:
            groups = Group().find_by_ids(group_ids)
            data['groups'] = groups

        if host_ids:
            hosts = Host().find_by_ids(host_ids)
            data['hosts'] = hosts

        return data

    def bind_roles(self, user_id, role_ids, add_by=None):
        collection = db.collection('user_roles')
        collection.delete_many({'user_id': user_id})
        inserted = []
        for role_id in role_ids:
            data = {
                'role_id': role_id,
                'user_id': user_id,
                'add_by': add_by,
                'created_at': time.time()
            }
            result = collection.insert_one(data)
            inserted.append(result.inserted_id)

        return inserted

    def add_user(self, user):
        username = user.get('username')
        password = user.get('password')
        email = user.get('email')
        phone = user.get('phone')
        if not username or not password or not email:
            return False, None

        where = {
            '$or': [
                {
                    'username': username,

                },
                {
                    'email': email,
                },
                {
                    'phone': phone
                }
            ]
        }

        existed = self.collection.find_one(where)
        if existed:
            return False, existed['_id']

        password = generate_password_hash(str(password))
        user['password'] = password
        user['created_at'] = time.time()
        result = self.collection.insert_one(user)

        return True, result.inserted_id

    @staticmethod
    def join_team(self):
        pass
