from channels.generic.websocket import AsyncJsonWebsocketConsumer

class AgentConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.group = self.scope["url_route"]["kwargs"]["group"]
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.group, self.channel_name)

    async def agent_message(self, event):
        await self.send_json(event["payload"])
