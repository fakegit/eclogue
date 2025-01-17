from bson import ObjectId
from flask import jsonify, request
from eclogue.middleware import jwt_required, login_user
from eclogue.models.job import Job
from eclogue.model import db
from eclogue.lib.workspace import Workspace
from eclogue.lib.helper import load_ansible_playbook
from eclogue.lib.integration import Integration

def gitlab_job(token):
    payload = request.get_json()
    object_type = payload.get('object_type')
    tag = payload.get('tag')
    job_id = payload.get('job_id')
    project_id = payload.get('project_id')
    job_status = payload.get('job_status')
    repository = payload.get('repository')
    record = Job().collection.find_one({'token': token})
    if not record:
        return jsonify({
            'message': 'invalid token',
            'code': 104010
        }), 401

    if object_type != 'job':
        return jsonify({
            'message': 'only job event allow',
            'code': 104031
        }), 403

    if not job_id or not project_id or job_status != 'success':
        return jsonify({
            'message': 'invalid params',
            'code': 104000
        }), 400

    if not tag:
        return jsonify({
            'message': 'only tag allow',
            'code': 104032
        }), 403

    app_info = db.collection('apps').find_one({'_id': ObjectId(record.get('app_id'))})
    if not app_info:
        return jsonify({
            'message': 'job must be bind with gitlab app',
            'code': 104002
        }), 400
    params = app_info.get('params') or {}
    if params.get('project_id') != project_id:
        return jsonify({
            'message': 'illegal project',
            'code': 104003
        }), 400

    # if params.get('extract') == 'artifacts':
    #     wk = Workspace()
    #     filename = wk.get_gitlab_artifacts_file(record.get('name'), project_id, job_id)
    #     gitlab = GitlabApi().dowload_artifact(project_id, job_id, filename)
    #
    # if params.get('extract') == 'docker':
    #     pass
    integration = Integration(app_info.get('type'), params)
    integration.install()

    ansible_params = load_ansible_playbook(record)
    if ansible_params.get('message') is not 'ok':
        return jsonify(payload), 400

    data = ansible_params.get('data')
    wk = Workspace()
    res = wk.load_book_from_db(name=data.get('book_name'), roles=data.get('roles'))
    if not res:
        return jsonify({
            'message': 'load book failed',
            'code': 104000,
        }), 400

    return jsonify({
        'message': 'ok',
        'code': 0,
        'data': 1
    })
