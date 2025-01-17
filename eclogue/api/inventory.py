import time
import datetime

from flask import request, jsonify
from bson import ObjectId
from tempfile import NamedTemporaryFile
from deepdiff import DeepDiff
from eclogue.middleware import jwt_required, login_user
from eclogue.model import db
from eclogue.config import config
from eclogue.lib.helper import process_ansible_setup
from eclogue.ansible.vault import Vault
from eclogue.lib.helper import parse_cmdb_inventory, parse_file_inventory
from eclogue.lib.player import setup
from eclogue.ansible.host import parser_inventory
from eclogue.lib.inventory import get_inventory_from_cmdb, get_inventory_by_book
from eclogue.models.host import host_model, Host
from eclogue.lib.logger import logger
from eclogue.models.region import Region
from eclogue.models.group import Group
from eclogue.models.credential import Credential


def get_inventory():
    query = request.args
    cmdb_type = query.get('type', 'cmdb')
    if cmdb_type == 'file':
        booke_id = query.get('book')
        book = db.collection('books').find_one({'_id': ObjectId(booke_id)})
        if not book:
            return jsonify({
                'message': 'invalid book',
                'code': 104041,
            }), 404

        hosts = get_inventory_by_book(book.get('_id'), book_name=book.get('name'))
    else:
        hosts = get_inventory_from_cmdb()

    return jsonify({
        'message': 'ok',
        'code': 0,
        'data': hosts,
    })


@jwt_required
def edit_inventory(_id):
    user = login_user
    payload = request.get_json()
    if not payload:
        return jsonify({
            'message': 'miss required params',
            'code': 124001,
        }), 400
    record = db.collection('machines').find_one({'_id': ObjectId(_id)})
    if not record:
        return jsonify({
            'message': 'record not found',
            'code': 124041
        }), 400

    payload.pop('_id')
    payload['updated_at'] = time.time()
    update = {
        '$set': payload
    }
    db.collection('machines').update_one({'_id': record['_id']}, update=update)
    logger.info('update machine', extra={'record': record, 'changed': payload})

    return jsonify({
        'message': 'ok',
        'code': 0,
        # 'data': diff
    })


@jwt_required
def delete_inventory(_id):
    host = Host()
    record = host.find_by_id(_id)
    if not record:
        return jsonify({
            'message': 'record not found',
            'code': 104040
        }), 404

    update = {
        '$set': {
            'status': -1,
            'delete_at': time.time(),
            'delete_by': login_user.get('username')
        }
    }

    host.collection.update_one({'_id': record['_id']}, update=update)
    msg = 'delete inventory:, hostname: {}'.format(record.get('hostname'))
    extra = {
        'record': record,
    }

    logger.info(msg, extra=extra)

    return jsonify({
        'message': 'ok',
        'code': 0,
    })

@jwt_required
def explore():
    payload = request.get_json()
    form = request.form
    payload = payload or form
    if not payload:
        return jsonify({
            'message': 'empty request payload',
            'code': 144000,
        }), 400

    explore_type = payload.get('type')
    credential = payload.get('credential')
    # if not credential:
    #     return jsonify({
    #         'message': 'param credential required',
    #         'code': 144000,
    #     }), 400

    private_key = ''
    if credential:
        credential = Credential.find_by_id(credential)
        if not credential or not credential.get('status'):
            return jsonify({
                'message': 'invalid credential',
                'code': 144040,
            }), 404

        vault = Vault({
            'vault_pass': config.vault.get('secret')
        })

        body = credential['body']
        private_key = vault.decrypt_string(body[credential['type']])

    maintainer = payload.get('maintainer')
    if not maintainer or type(maintainer) != list:
        maintainer = [login_user.get('username')]
    else:
        maintainer.extend(login_user.get('username'))

    if explore_type == 'manual':
        region = payload.get('region')
        group = payload.get('group')
        ssh_host = payload.get('ssh_host')
        ssh_user = payload.get('ssh_user')
        ssh_port = payload.get('ssh_port') or 22
        if not ssh_host or not ssh_user or not ssh_port:
            return jsonify({
                'message': 'illegal ssh connection params',
                'code': 144001,
            }), 400

        region_record = Region.find_one({'_id': ObjectId(region)})
        if not region_record:
            return jsonify({
                'message': 'invalid region',
                'code': 144002,
            }), 400

        group_record = Group.find_by_ids(group)
        if not group_record:
            return jsonify({
                'message': 'invalid group',
                'code': 144003,
            }), 400

        options = {
            'remote_user': ssh_user,
            'verbosity': 3,
        }
        hosts = ssh_host + ':' + str(ssh_port) + ','
        runner = setup(hosts, options, private_key)
        result = runner.get_result()
        data = process_ansible_setup(result)
        records = []
        if not data:
            return jsonify({
                'code': 144009,
                'message': 'fetch target host failed',
                'data': result
            }), 406

        for item in data:
            item['ansible_ssh_host'] = ssh_host
            item['ansible_ssh_user'] = ssh_user
            item['ansible_ssh_port'] = ssh_port
            item['maintainer'] = maintainer
            item['group'] = list(map(lambda i: str(i['_id']), group_record))
            item['add_by'] = login_user.get('username')
            item['state'] = 'active'
            where = {'ansible_ssh_host': item['ansible_ssh_host']}
            update = {'$set': item}
            result = db.collection('machines').update_one(where, update, upsert=True)
            extra = item.copy()
            extra['_id'] = result.upserted_id
            logger.info('add machines hostname: '.format({item['hostname']}), extra={'record': data})
            records.append(item)
        # def func(item):
        #     item['ansible_ssh_host'] = ssh_host
        #     item['ansible_ssh_user'] = ssh_user
        #     item['ansible_ssh_port'] = ssh_port
        #     item['maintainer'] = maintainer
        #     item['group'] = list(map(lambda i: str(i['_id']), group_record))
        #     item['add_by'] = login_user.get('username')
        #     item['state'] = 'active'
        #
        #     return item
        #
        # data = list(map(func, data))
        # db.collection('machines').insert_many(data)

        return jsonify({
            'message': 'ok',
            'code': 0,
            'data': records,
            'records': data
        })

    files = request.files
    if not files:
        return jsonify({
            'message': 'illegal param',
            'code': 104000,
        }), 400

    file = files.get('inventory')
    if not files:
        return jsonify({
            'message': 'files required',
            'code': 104001,
        }), 400

    sources = file.read().decode('utf-8')
    # inventory is not only yaml
    with NamedTemporaryFile('w+t', delete=True) as fd:
        fd.write(sources)
        fd.seek(0)
        options = {
            'verbosity': 0,
        }
        runner = setup(fd.name, options, private_key)
        result = runner.get_result()
        data = process_ansible_setup(result)
        if not data:
            return jsonify({
                'code': 144009,
                'message': 'fetch target host failed',
                'data': result
            }), 400

        manager = runner.inventory
        hosts = parser_inventory(manager)
        records = []
        default_region = db.collection('regions').find_one({'name': 'default'})
        if not default_region:
            result = db.collection('regions').insert_one({
                'name': 'default',
                'add_by': None,
                'description': 'auto generate',
                'created_at': time.time(),
            })
            region_id = str(result.inserted_id)
        else:
            region_id = str(default_region.get('_id'))

        for node in data:
            hostname = node.get('ansible_hostname')
            for group, host in hosts.items():
                where = {'name': group}
                # insert_data = {'$set': insert_data}
                existed = db.collection('groups').find_one(where)
                if not existed:
                    insert_data = {
                        'name': group,
                        'region': region_id,
                        'description': 'auto generator',
                        'state': 'active',
                        'add_by': login_user.get('username'),
                        'maintainer': None,
                        'created_at': int(time.time())
                    }
                    insert_result = db.collection('groups').insert_one(insert_data)
                    group = insert_result.inserted_id
                else:
                    group = existed['_id']

                if host.get('name') == hostname:
                    vars = host.get('vars')
                    node['ansible_ssh_host'] = vars.get('ansible_ssh_host')
                    node['ansible_ssh_user'] = vars.get('ansible_ssh_user', 'root')
                    node['ansible_ssh_port'] = vars.get('ansible_ssh_port', '22')
                    node['group'] = [group]
                    node['add_by'] = login_user.get('username')
                    node['state'] = 'active'

                    break

            records.append(node)

        for record in records:
            where = {'ansible_ssh_host': record['ansible_ssh_host']}
            update = {'$set': record}
            result = db.collection('machines').update_one(where, update, upsert=True)
            extra = record.copy()
            extra['_id'] = result.upserted_id
            logger.info('add machines hostname: '.format({record['hostname']}), extra={'record': data})

        return jsonify({
            'message': 'ok',
            'code': 0,
            'data': data,
            'records': records,
        })


def test():
    # jks.save_artifacts(config.workspace['tmp'], 'upward', '18')
    filename = config.workspace.get('tmp') + '/hosts'
    result = parser_inventory(filename)
    return jsonify({
        'message': 'ok',
        'code': 0,
        'data': result
    })


def regions():
    query = request.args
    keyword = query.get('keyword')
    start = query.get('start')
    end = query.get('end')
    platform = query.get('platform')
    where = dict()
    if platform:
        where['platform'] = platform

    if keyword:
        where['name'] = {
            '$regex': keyword
        }

    date = []
    if start:
        date.append({
            'created_at': {
                '$gte': int(time.mktime(time.strptime(start, '%Y-%m-%d')))
            }
        })

    if end:
        date.append({
            'created_at': {
                '$lte': int(time.mktime(time.strptime(end, '%Y-%m-%d')))
            }
        })

    if date:
        where['$and'] = date

    records = db.collection('regions').find(where)

    return jsonify({
        'message': 'ok',
        'code': 0,
        'data': {
            'list': list(records)
        }
    })


@jwt_required
def add_region():
    body = request.get_json()
    if not body:
        return jsonify({
            'message': 'invalid params',
            'code': 104000
        }), 400

    name = body.get('name')
    description = body.get('description')
    bandwidth = body.get('bandwidth')
    contact = body.get('contact')
    ip_range = body.get('ip_range')
    platform = body.get('platform')
    exists = Region.find_one({'name': name})
    if exists:
        return jsonify({
            'message': 'name existed',
            'code': 104880
        }), 400

    record = {
        'name': name,
        'description': description,
        'bandwidth': bandwidth,
        'contact': contact,
        'ip_range': ip_range,
        'platform': platform
    }

    Region.insert_one(record)

    return jsonify({
        'message': 'ok',
        'code': 0,
    })


def update_region(_id):
    where = {
        '_id': ObjectId(_id)
    }
    record = db.collection('regions').find_one(where)
    if not record:
        return jsonify({
            'message': 'record not found',
            'code': '124040'
        }), 404

    payload = request.get_json()
    if not payload:
        return jsonify({
            'message': 'miss required params',
            'code': 124001
        }), 400
    data = dict()
    allow_fields = [
        'platform',
        'ip_range',
        'bandwidth',
        'contact',
        'name',
        'description'
    ]
    for key, value in payload.items():
        if key in allow_fields:
            data[key] = value

    db.collection('regions').update_one(where, {'$set': data})
    data['_id'] = _id
    logger.info('update region', extra={'record': record, 'changed': data})

    return jsonify({
        'message': 'ok',
        'code': 0,
    })


@jwt_required
def groups():
    query = request.args or {}
    keyword = query.get('keyword')
    start = query.get('start')
    end = query.get('end')
    page = int(query.get('page', 1))
    limit = int(query.get('pageSize', 50))
    region = query.get('region')
    where = {
        'status': {
            '$ne': -1
        }
    }
    if region:
        where['region'] = query.get('region')

    if keyword:
        where['name'] = {
            '$regex': keyword
        }

    date = []
    if start:
        date.append({
            'created_at': {
                '$gte': int(time.mktime(time.strptime(start, '%Y-%m-%d')))
            }
        })

    if end:
        date.append({
            'created_at': {
                '$lte': int(time.mktime(time.strptime(end, '%Y-%m-%d')))
            }
        })

    if date:
        where['$and'] = date

    offset = (page - 1) * limit
    is_all = query.get('all')
    if is_all and login_user.get('is_admin'):
        records = db.collection('groups').find({})
    else:
        records = db.collection('groups').find(where, limit=limit, skip=offset)
    total = records.count()
    records = list(records)
    for group in records:
        region = db.collection('regions').find_one({'_id': ObjectId(group['region'])})
        group['region_name'] = region.get('name')

    return jsonify({
        'message': 'ok',
        'code': 0,
        'data': {
            'list': list(records),
            'page': page,
            'pagesize': limit,
            'total': total
        }
    })


@jwt_required
def add_group():
    user = login_user
    payload = request.get_json()
    if not payload:
        return jsonify({
            'message': 'invalid params',
            'code': 124003
        }), 400
    region = payload.get('region')
    name = payload.get('name')
    if not payload.get('name') or not payload.get('region'):
        return jsonify({
            'message': 'invalid params',
            'code': 124004
        }), 400
    dc = db.collection('regions').find_one({'_id': ObjectId(region)})
    if not dc:
        return jsonify({
            'message': 'data center existed',
            'code': 124005,
        }), 400
    check = db.collection('groups').find_one({'name': name})
    if check:
        return jsonify({
            'message': 'group existed',
            'code': 124004,
        }), 400

    data = {
        'name': name,
        'region': region,
        'add_by': user.get('username'),
        'description': payload.get('description', ''),
        'created_at': int(time.time())
    }
    result = db.collection('groups').insert_one(data)
    data['_id'] = result.inserted_id
    logger.info('add group', extra={'record': data})

    return jsonify({
        'message': 'ok',
        'code': 0,
    })


def update_group(_id):
    where = {
        '_id': ObjectId(_id)
    }
    record = db.collection('groups').find_one(where)
    if not record:
        return jsonify({
            'message': 'record not found',
            'code': '124040'
        }), 404

    payload = request.get_json()
    if not payload:
        return jsonify({
            'message': 'miss required params',
            'code': 124001
        }), 400

    data = dict()
    for key, value in payload.items():
        if record.get('key'):
            data[key] = value

    db.collection('regions').update_one(where, {'$set', data})
    logger.info('update group', extra={'record': record, 'changed': data})

    return jsonify({
        'message': 'ok',
        'code': 0,
    })


def preview_inventory():
    payload = request.get_json()
    inventory_type = payload.get('inventory_type', 'file')
    inventory = payload.get('inventory', None)
    if not inventory:
        return jsonify({
            'message': 'invalid param inventory',
            'code': 14002
        }), 400

    if inventory_type == 'file':
        result = parse_file_inventory(inventory)
    else:
        result = parse_cmdb_inventory(inventory)

    if not result:
        return jsonify({
            'message': 'invalid inventory',
            'code': 104003,
        }), 400

    return jsonify({
        'message': 'ok',
        'code': 0,
        'data': result,
    })


@jwt_required
def host_tree():
    user_id = login_user.get('user_id')
    is_admin = login_user.get('is_admin')
    if is_admin:
        groups = db.collection('groups').find({})
        group_ids = map(lambda i: i['_id'], groups)
        group_ids = list(group_ids)

    condition = [{
        '$group': {
            '_id': '$type',
            'count': {
                '$sum': 1
            }
        },
        '$match': {
            'user_id': user_id,
        }
    }]
    result = db.collection('user_hosts').aggregate(condition)

    return jsonify({
        'message': 'ok',
        'code': 0,
        'data': [],
    })


@jwt_required
def get_group_hosts(_id):
    user_id = login_user.get('user_id')
    is_admin = login_user.get('is_admin')
    # @todo super admin
    where = {
        'user_id': user_id,
        'group_id': _id,
    }
    records = db.collection('user_hosts').find(where)
    hids = map(lambda i: ObjectId(i.get('host_id')), records)
    hosts = db.collection('machines').find({'_id': {
        '$in': list(hids)
    }})

    return jsonify({
        'message': 'ok',
        'code': 0,
        'data': {
            'group': _id,
            'hosts': list(hosts),
        }
    })


@jwt_required
def get_devices():
    query = request.args
    page = int(query.get('page', 1))
    limit = int(query.get('pageSize', 50))
    skip = (page - 1) * limit
    where = {
        'status': {
            '$ne': -1
        }
    }
    hostname = query.get('hostname')
    group = query.get('group')
    region = query.get('region')
    status = query.get('status')
    start = query.get('start')
    end = query.get('end')
    if hostname:
        where['hostname'] = hostname

    if status:
        where['status'] = status

    date = []
    if start:
        date.append({
            'created_at': {
                '$gte': int(time.mktime(time.strptime(start, '%Y-%m-%d')))
            }
        })

    if end:
        date.append({
            'created_at': {
                '$lte': int(time.mktime(time.strptime(end, '%Y-%m-%d')))
            }
        })

    if date:
        where['$and'] = date

    if region:
        record = Region.find_by_id(region)
        if not record:
            return jsonify({
                'message': 'illegal param',
                'code': 104001
            }), 400

        group_records = Group().collection.find({'region': region})
        g_ids = []
        for item in group_records:
            g_ids.append(item['_id'])

        where['group'] = {
            '$in': g_ids,
        }

    if group:
        where['group'] = {
            '$in': [group],
        }

    result = db.collection('machines').find(where).skip(skip=skip).limit(limit)
    total = result.count()
    result = list(result)
    collection = Group()
    for device in result:
        ids = device.get('group') or []
        if ids != ['ungrouped']:
            records = collection.find_by_ids(ids)
            records = list(records)
            records = map(lambda i: i['name'], records)
            device['group_names'] = list(records)
        else:
            device['group_names'] = ['ungrouped']

    return jsonify({
        'message': 'ok',
        'code': 0,
        'data': {
            'list': result,
            'total': total,
            'page': page,
            'pageSize': limit,
        },
    })


@jwt_required
def get_host_groups(user_id):
    current_user_id = login_user.get('user_id')
    # query = request.args
    # page = int(query.get('page', 1))
    # limit = int(query.get('pageSize', 20))
    # skip = (page - 1) * limit
    if current_user_id != user_id:
        return jsonify({
            'message': 'invalid user',
            'code': 104030
        })

    tree = get_inventory_from_cmdb()

    return jsonify({
        'message': 'ok',
        'code': 0,
        'data': tree,
    })


@jwt_required
def get_node_info(_id):
    record = host_model.find_by_id(_id)
    if not record:
        return jsonify({
            'message': 'record not found',
            'code': 104040
        }), 404

    return jsonify({
        'message': 'ok',
        'code': 0,
        'data': record
    })


@jwt_required
def get_group_info(_id):
    if _id == 'ungrouped':
        record = {
            '_id': _id,
            'name': _id,
            'description': _id,
            'region': {
                'name': 'ungrouped'
            }
        }
    else:
        record = db.collection('groups').find_one({'_id': ObjectId(_id)})
        if not record:
            return jsonify({
                'message': 'record not found',
                'code': 104040
            }), 404

        dc = db.collection('regions').find_one({
            '_id': ObjectId(record.get('region'))
        })
        record['region'] = dc or {}

    return jsonify({
        'message': 'ok',
        'code': 0,
        'data': record
    })


@jwt_required
def delete_group(_id):
    record = db.collection('groups').find_one({'_id': ObjectId(_id)})
    if not record:
        return jsonify({
            'message': 'record not found',
            'code': 104040,
        }), 404

    if not login_user.get('is_admin'):
        return jsonify({
            'message': 'permission deny',
            'code': 104030,
        }), 403

    if not record.get('add_by'):
        return jsonify({
            'message': 'protected record',
            'code': 10086
        }), 400

    update = {
        '$set': {
            'status': -1,
            'delete_at': time.time(),
            'delete_by': login_user.get('username')
        }
    }

    group_id = str(record['_id'])
    db.collection('groups').update_one({'_id': record['_id']}, update=update)
    where = {
        'group': {
            '$in': [group_id]
        }
    }
    Host().collection.update_many(where, {
        '$pull': {
            'group': group_id
        }
    })
    msg = 'delete inventory:, name: {}'.format(record.get('name'))
    extra = {
        'record': record,
    }
    logger.info(msg, extra=extra)

    return jsonify({
        'message': 'ok',
        'code': 0,
    })


@jwt_required
def get_device_info(_id):
    record = db.collection('machines').find_one({'_id': ObjectId(_id)})
    if not record:
        return jsonify({
            'message': 'record not found',
            'code': 104040,
        }), 404

    where = {
        'id': {
            '$in': record.get('group')
        }
    }
    groups = db.collection('groups').find(where)
    group_names = map(lambda i: i['name'], groups)
    group_names = list(group_names)
    record['group_names'] = group_names

    return jsonify({
        'message': 'ok',
        'code': 0,
        'data': record,
    })
