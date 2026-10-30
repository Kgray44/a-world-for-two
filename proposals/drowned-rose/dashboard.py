"""Proposed Control Room service. Master integrates into control_room/tavern.py."""
from datetime import datetime, timezone
import json
from pathlib import Path
import re


class Tavern:
    def __init__(self,home,send_command):
        self.path=Path(home)/'dashboard/tavern/status.json'
        self.send_command=send_command

    def snapshot(self):
        if not self.path.is_file() or self.path.stat().st_size>128*1024:
            return {'current':False,'reason':'Tavern telemetry unavailable','residents':[]}
        try:
            data=json.loads(self.path.read_bytes())
            age=(datetime.now(timezone.utc)-datetime.fromisoformat(data['at'].replace('Z','+00:00'))).total_seconds()
            if not isinstance(data['residents'],list)or len(data['residents'])>45:raise ValueError('Invalid resident count')
            data['current']=-2<=age<=15;data['age_seconds']=age
            if not data['current']:data['reason']='Tavern telemetry is stale'
            return data
        except (ValueError,KeyError,TypeError):
            return {'current':False,'reason':'Invalid tavern telemetry','residents':[]}

    def control(self,body):
        status=self.snapshot()
        if not status['current']:raise ValueError('Fresh tavern telemetry required')
        action=body.get('action')
        if action=='music':
            if type(body.get('enabled'))is not bool:raise ValueError('Boolean enabled required')
            command='awfttavern music '+str(body['enabled']).lower()
        elif action in {'enabled','recover','weight'}:
            ident=body.get('id','')
            if not re.fullmatch('[a-z][a-z0-9-]{1,48}',ident)or ident not in {r['id']for r in status['residents']}:raise ValueError('Unknown resident')
            prefix='awfttavern resident '+ident+' '
            if action=='enabled':
                if type(body.get('enabled'))is not bool:raise ValueError('Boolean enabled required')
                command=prefix+'enabled '+str(body['enabled']).lower()
            elif action=='recover':command=prefix+'recover'
            else:
                if body.get('activity')not in {'sit','social','walk','bar','watch','window','group','return','drink'}:raise ValueError('Unknown activity')
                if type(body.get('weight'))is not int or not 1<=body['weight']<=12:raise ValueError('Weight1..12 required')
                command=prefix+'weight '+body['activity']+' '+str(body['weight'])
        else:raise ValueError('Unknown tavern action')
        self.send_command(command,confirmed=True)
        return {'requested':True,'runtime_acknowledged':False,'command':command}


# Add ONLY these fullmatch patterns to the existing server command allowlist.
COMMAND_PATTERNS=(
    r'awfttavern (?:status|inspect)',
    r'awfttavern initialize [a-f0-9]{64}',
    r'awfttavern suspend (?:true|false)',
    r'awfttavern music (?:true|false)',
    r'awfttavern resident [a-z][a-z0-9-]{1,48} (?:enabled (?:true|false)|recover)',
    r'awfttavern resident [a-z][a-z0-9-]{1,48} weight (?:sit|social|walk|bar|watch|window|group|return|drink) (?:[1-9]|1[0-2])',
)
