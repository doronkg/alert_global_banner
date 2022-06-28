import re
import sys
import json
import time
import requests
from   urllib3.exceptions import InsecureRequestWarning

def get_time_multiplier(time_specifier):
    return {
        's': 1,
        'm': 60,
        'h': 3600,
        'd': 86400
    }[time_specifier]

def update_global_banner(settings, visible, message, background_color, hyperlink, hyperlink_text):
    url     = '%s/servicesNS/nobody/system/data/ui/global-banner/BANNER_MESSAGE_SINGLETON' % settings.get('server_uri')
    headers = { 'Authorization' : 'Splunk %s' % settings.get('session_key') }
    data    = {
                'global_banner.visible'          : visible,
                'global_banner.message'          : message,
                'global_banner.background_color' : background_color,
                'global_banner.hyperlink'        : hyperlink,
                'global_banner.hyperlink_text'   : hyperlink_text
              }

    try:
        req = requests.post(url, data=data, headers=headers, verify=False)
        if 200 <= req.status_code < 300:
            sys.stderr.write('DEBUG global-banner endpoint responded with HTTP status=%d\n'
                              % req.status_code)
            return True
        else:
            sys.stderr.write('ERROR global-banner endpoint responded with HTTP status=%d\n'
                              % req.status_code)
            return False
    except Exception as e:
        sys.stderr.write('ERROR Error %s\n' % e)
    return False

def update_expiration_timeout(settings, trigger_time, expiration_timeout, sid):
    url     = '%s/servicesNS/nobody/alert_banner/storage/collections/data/global_banner_expiration_collection' % settings.get('server_uri')
    headers = {
                 'Authorization' : 'Splunk %s' % settings.get('session_key'),
                 'Content-Type'  : 'application/json'
              }
    data    = {
                'trigger_time'       : trigger_time,
                'expiration_timeout' : expiration_timeout,
                'sid'                : sid
              }

    try:
        req = requests.post(url, data=json.dumps(data), headers=headers, verify=False)
        if 200 <= req.status_code < 300:
            sys.stderr.write('DEBUG collection endpoint responded with HTTP status=%d\n'
                              % req.status_code)
            return True
        else:
            sys.stderr.write('ERROR collection endpoint responded with HTTP status=%d\n'
                              % req.status_code)
            return False
    except Exception as e:
        sys.stderr.write('ERROR Error %s\n' % e)
    return False

def validate_latest_update(settings, sid):
    query = '''
            | inputlookup global_banner_expiration_lookup
            | eval _time = trigger_time
            | stats latest(sid) AS sid
            | eval is_latest=if(sid=="%s", "True", "False")
            | table is_latest
            ''' % sid
    url     = '%s/services/search/jobs/export' % settings.get('server_uri')
    headers = { 'Authorization' : 'Splunk %s' % settings.get('session_key') }
    params  = { 'output_mode' : 'json' }
    data    = 'search=' + query

    try:
        req = requests.post(url, data=data, params=params, headers=headers, verify=False)
        if 200 <= req.status_code < 300:
            sys.stderr.write('DEBUG search endpoint responded with HTTP status=%d\n'
                              % req.status_code)
            return req.json()['result']['is_latest']
        else:
            sys.stderr.write('ERROR search endpoint responded with HTTP status=%d\n'
                              % req.status_code)
            return False
    except Exception as e:
        sys.stderr.write('ERROR Error %s\n' % e)
    return False

def disable_global_banner(settings):
    url     = '%s/servicesNS/nobody/system/data/ui/global-banner/BANNER_MESSAGE_SINGLETON' % settings.get('server_uri')
    headers = { 'Authorization' : 'Splunk %s' % settings.get('session_key') }
    data    = { 'global_banner.visible' : 'false' }

    try:
        req = requests.post(url, data=data, headers=headers, verify=False)
        if 200 <= req.status_code < 300:
            sys.stderr.write('DEBUG global-banner endpoint responded with HTTP status=%d\n'
                              % req.status_code)
            return True
        else:
            sys.stderr.write('ERROR global-banner endpoint responded with HTTP status=%d\n'
                              % req.status_code)
            return False
    except Exception as e:
        sys.stderr.write('ERROR Error %s\n' % e)
    return False

if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] != '--execute':
        sys.stderr.write('FATAL Unsupported execution mode (expected --execute flag)\n')
        sys.exit(1)
    try:
        requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

        settings = json.loads(sys.stdin.read())
        config = settings['configuration']
        sys.stderr.write('DEBUG Alert Action Payload: ' + str(config))

        successfull_global_banner_update = update_global_banner(
            settings, 
            visible=config.get('visible'), 
            message=config.get('message'), 
            background_color=config.get('background_color'), 
            hyperlink=config.get('hyperlink'), 
            hyperlink_text=config.get('hyperlink_text'))
        if not successfull_global_banner_update:
            sys.exit(2)

        successfull_expiration_update = update_expiration_timeout(
            settings, 
            trigger_time=config.get('trigger_time'),
            expiration_timeout=config.get('expiration_timeout'),
            sid=config.get('sid'))
        if not successfull_expiration_update:
            sys.exit(3)

        expiration_timeout = config.get('expiration_timeout') 
        time_period = re.findall(r'\d+', expiration_timeout)[0]
        time_specifier = re.findall(r"[s|m|h|d]", expiration_timeout)[0]
        time_to_sleep = int(time_period) * get_time_multiplier(time_specifier)
        time.sleep(time_to_sleep)

        successfull_validation = validate_latest_update(
            settings,
            sid=config.get('sid'))
        if not successfull_validation:
            sys.exit(4)
        else:
            successfull_global_banner_disabling = disable_global_banner(settings)
            if not successfull_global_banner_disabling:
                sys.exit(5)

    except Exception as e:
        sys.stderr.write('ERROR Unexpected error: %s\n' % e)
        sys.exit(6)
