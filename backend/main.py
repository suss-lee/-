from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict

app = FastAPI(title="Danggeun Market Basic MVP")

# 프론트엔드 연동 CORS 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------- 기본 인메모리 데이터 -----------------
IS_TEST_MODE = True  # 가상(Mock) GPS 인증 모드

posts = [
    {
        "id": 2,
        "seller_name": "성수장인",
        "title": "아이패드 에어 5세대 64GB",
        "price": 620000,
        "content": "기스 하나 없는 S급입니다. 성수역 직거래 희망해요.",
        "town": "성수동",
        "created_at": "방금 전"
    },
    {
        "id": 1,
        "seller_name": "성수장인",
        "title": "블루투스 기계식 키보드",
        "price": 45000,
        "content": "박스 풀셋입니다. 타건감 좋아요.",
        "town": "성수동",
        "created_at": "1시간 전"
    }
]

# ----------------- 1. GPS 동네 인증 API (Mock) -----------------
@app.post("/api/town/verify")
def verify_town():
    if IS_TEST_MODE:
        return {
            "status": "SUCCESS",
            "town": "성수동",
            "message": "성수동 동네 인증이 완료되었습니다. (가상 위치 모드)"
        }
    return {"status": "FAIL", "message": "위치 인증 실패"}

# ----------------- 2. 홈 피드 목록 조회 API -----------------
@app.get("/api/posts")
def get_posts():
    # 최신순(id 역순) 정렬 반환
    return sorted(posts, key=lambda x: x["id"], reverse=True)

# ----------------- 3. 게시글 상세 조회 API -----------------
@app.get("/api/posts/{post_id}")
def get_post_detail(post_id: int):
    for post in posts:
        if post["id"] == post_id:
            return post
    raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")

# ----------------- 4. 판매글 등록 API -----------------
class PostCreateReq(BaseModel):
    seller_name: str
    title: str
    price: int
    content: str
    town: str

@app.post("/api/posts")
def create_post(req: PostCreateReq):
    new_id = len(posts) + 1
    new_post = {
        "id": new_id,
        "seller_name": req.seller_name,
        "title": req.title,
        "price": req.price,
        "content": req.content,
        "town": req.town,
        "created_at": "방금 전"
    }
    posts.append(new_post)
    return {"status": "SUCCESS", "post": new_post}

# ----------------- 5. 실시간 1:1 채팅 웹소켓 -----------------
class ChatConnectionManager:
    def __init__(self):
        self.active_rooms: Dict[int, List[WebSocket]] = {}

    async def connect(self, room_id: int, websocket: WebSocket):
        await websocket.accept()
        if room_id not in self.active_rooms:
            self.active_rooms[room_id] = []
        self.active_rooms[room_id].append(websocket)

    def disconnect(self, room_id: int, websocket: WebSocket):
        if room_id in self.active_rooms and websocket in self.active_rooms[room_id]:
            self.active_rooms[room_id].remove(websocket)

    async def broadcast(self, room_id: int, message: str):
        if room_id in self.active_rooms:
            for connection in self.active_rooms[room_id]:
                await connection.send_text(message)

chat_manager = ChatConnectionManager()

@app.websocket("/ws/chat/{post_id}")
async def chat_endpoint(websocket: WebSocket, post_id: int):
    await chat_manager.connect(post_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await chat_manager.broadcast(post_id, data)
    except WebSocketDisconnect:
        chat_manager.disconnect(post_id, websocket)
