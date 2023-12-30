import os
import CloudFlare
import waitress
import flask


app = flask.Flask(__name__)


@app.route('/', methods=['GET'])
def main():
    token = flask.request.args.get('token')
    zone = flask.request.args.get('zone')
    record = flask.request.args.get('record')
    ipv4 = flask.request.args.get('ipv4')
    ipv6 = flask.request.args.get('ipv6')
    cf = CloudFlare.CloudFlare(token=token)

    if not token:
        return flask.jsonify({'status': 'error', 'message': 'Missing token URL parameter.'}), 400
    if not zone:
        return flask.jsonify({'status': 'error', 'message': 'Missing zone URL parameter.'}), 400
    if not ipv4 and not ipv6:
        return flask.jsonify({'status': 'error', 'message': 'Missing ipv4 or ipv6 URL parameter.'}), 400

    try:
        zones = cf.zones.get(params={'name': zone})

        if not zones:
            return flask.jsonify({'status': 'error', 'message': 'Zone {} does not exist.'.format(zone)}), 404
        
        # Not sure if this will still work, need to test
        record_zone_concat = '{}.{}'.format(record, zone) if record is not None else zone

        cfParams = { 'match': 'all' }

        if record:
            cfParams['name'] = record_zone_concat

        cfParams['type'] = 'A'
        a_records = cf.zones.dns_records.get(zones[0]['id'], params=cfParams)
        cfParams['type'] = 'AAAA'
        aaaa_records = cf.zones.dns_records.get(zones[0]['id'], params=cfParams)

        for a_record in a_records:
            if ipv4 is not None and not a_record:
                return flask.jsonify({'status': 'error', 'message': f'A record for {record_zone_concat} does not exist.'}), 404
            
            if ipv4 is not None and a_record['content'] != ipv4:
                cf.zones.dns_records.patch(zones[0]['id'], a_record['id'], data={'content': ipv4})

        for aaaa_record in aaaa_records:
            if ipv6 is not None and not aaaa_record:
                return flask.jsonify({'status': 'error', 'message': f'AAAA record for {record_zone_concat} does not exist.'}), 404

            if ipv6 is not None and aaaa_record['content'] != ipv6:
                cf.zones.dns_records.patch(zones[0]['id'], aaaa_record['id'], data={'content': ipv6})
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        return flask.jsonify({'status': 'error', 'message': str(e)}), 500

    return flask.jsonify({'status': 'success', 'message': 'Update successful.'}), 200


@app.route('/healthz', methods=['GET'])
def healthz():
    return flask.jsonify({'status': 'success', 'message': 'OK'}), 200


app.secret_key = os.urandom(24)
waitress.serve(app, host='0.0.0.0', port=80)
