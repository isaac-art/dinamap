import re
import os
import json
import time
from uuid import uuid4 as u4
from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from typing import Dict, Set
import asyncio

from data_utils import *

app = FastAPI()
app.add_middleware(CORSMiddleware,allow_origins=["*"],  allow_credentials=True,allow_methods=["*"], allow_headers=["*"],)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.player_data: Dict[str, dict] = {}
        
    async def connect(self, websocket: WebSocket, uid: str):
        await websocket.accept()
        self.active_connections[uid] = websocket
        
        # Send current players to the new connection
        await websocket.send_json({
            "type": "players_list",
            "players": self.player_data
        })
        
        # Notify others about new player
        await self.broadcast_except(uid, {
            "type": "player_joined",
            "uid": uid,
            "data": self.player_data.get(uid, {})
        })
        
    def disconnect(self, uid: str):
        if uid in self.active_connections:
            del self.active_connections[uid]
        if uid in self.player_data:
            del self.player_data[uid]
            
        # Notify others about player leaving
        asyncio.create_task(self.broadcast({
            "type": "player_left",
            "uid": uid
        }))
            
    async def update_player(self, uid: str, data: dict):
        self.player_data[uid] = data
        
        # Broadcast update to all other players
        await self.broadcast_except(uid, {
            "type": "player_update",
            "uid": uid,
            "data": data
        })
        
    async def broadcast(self, message: dict):
        disconnected = []
        for uid, connection in self.active_connections.items():
            try:
                await connection.send_json(message)
            except:
                disconnected.append(uid)
                
        # Clean up disconnected clients
        for uid in disconnected:
            self.disconnect(uid)
            
    async def broadcast_except(self, exclude_uid: str, message: dict):
        disconnected = []
        for uid, connection in self.active_connections.items():
            if uid != exclude_uid:
                try:
                    await connection.send_json(message)
                except:
                    disconnected.append(uid)
                    
        # Clean up disconnected clients
        for uid in disconnected:
            self.disconnect(uid)

manager = ConnectionManager()

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return FileResponse("static/index.html")

@app.get("/video-test")
async def video_test():
    return FileResponse("static/video_test.html")

@app.get("/stats")
async def stats():
    try: return generate_stats()
    except ValueError as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/user/{uid}")
async def get_user(uid: str):
    try:
        if not os.path.exists("main.json"): raise HTTPException(status_code=404, detail="User not found")
        with open("main.json", 'r') as f: data = json.load(f)
        if uid not in data: raise HTTPException(status_code=404, detail="User not found")
        user_data = data[uid]
        return {
            "uid": uid,
            "avatar": user_data.get("avatar"),
            "saved": user_data.get("saved", []),
            "start": user_data.get("start")
        }
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error loading user data: {str(e)}")

@app.post("/begin")
async def begin():
    uid = u4()
    update_json(uid, "start", time.time())
    return {"uid": str(uid)}


@app.post("/avatar")
async def avatar(request: Request):
    try:
        body = await request.json()
        
        # Validate request body
        if not isinstance(body, dict):
            raise HTTPException(status_code=400, detail="Request body must be a JSON object")
        
        uid = body.get("uid")
        avatar_id = body.get("avatar_id")
        
        if not uid or avatar_id is None:
            raise HTTPException(status_code=400, detail="Missing uid or avatar_id")
        
        # Validate avatar_id
        if not isinstance(avatar_id, (str, int)):
            raise HTTPException(status_code=400, detail="avatar_id must be a string or integer")
        
        update_json(uid, "avatar", avatar_id)
        return {"message": "Avatar updated successfully"}
        
    except json.JSONDecodeError: raise HTTPException(status_code=400, detail="Invalid JSON in request body")
    except ValueError as e: raise HTTPException(status_code=400, detail=str(e))


@app.post("/save")
async def save(request: Request):
    try:
        body = await request.json()
        if not isinstance(body, dict): raise HTTPException(status_code=400, detail="Request body must be a JSON object")
        
        uid = body.get("uid")
        saved_ids = body.get("saved_ids")
        
        if not uid or saved_ids is None: raise HTTPException(status_code=400, detail="Missing uid or saved_ids")
        
        if not isinstance(saved_ids, (list, str, int)): raise HTTPException(status_code=400, detail="saved_ids must be a list, string, or integer")
        
        update_json(uid, "saved", saved_ids)
        return {"message": "Data saved successfully"}
        
    except json.JSONDecodeError: raise HTTPException(status_code=400, detail="Invalid JSON in request body")
    except ValueError as e: raise HTTPException(status_code=400, detail=str(e))

@app.get("/editor")
async def editor():
    return FileResponse("static/editor.html")

@app.websocket("/ws/{uid}")
async def websocket_endpoint(websocket: WebSocket, uid: str):
    await manager.connect(websocket, uid)
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            if data.get("type") == "player_update":
                # Update player position and avatar
                await manager.update_player(uid, {
                    "x": data.get("x"),
                    "y": data.get("y"),
                    "avatar": data.get("avatar"),
                    "facingLeft": data.get("facingLeft", False)
                })
            elif data.get("type") == "ping":
                # Respond to ping to keep connection alive
                await websocket.send_json({"type": "pong"})
                
    except WebSocketDisconnect:
        manager.disconnect(uid)
    except Exception as e:
        print(f"WebSocket error for {uid}: {e}")
        manager.disconnect(uid)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8088)
