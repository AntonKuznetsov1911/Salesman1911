from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models for Objections
class ObjectionResponse(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Objection(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    responses: List[ObjectionResponse]
    category: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    is_favorite: bool = Field(default=False)
    usage_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class ObjectionCreate(BaseModel):
    title: str
    responses: List[str]
    category: Optional[str] = None
    tags: List[str] = Field(default_factory=list)

class ObjectionUpdate(BaseModel):
    title: Optional[str] = None
    responses: Optional[List[str]] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    is_favorite: Optional[bool] = None

class Quote(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str
    author: str
    category: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class QuoteCreate(BaseModel):
    text: str
    author: str
    category: Optional[str] = None

# Legacy models for status check
class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StatusCheckCreate(BaseModel):
    client_name: str

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "ПРОДАЖНИК API v1.0"}

# Legacy status check endpoints
@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.dict()
    status_obj = StatusCheck(**status_dict)
    _ = await db.status_checks.insert_one(status_obj.dict())
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find().to_list(1000)
    return [StatusCheck(**status_check) for status_check in status_checks]

# Objections endpoints
@api_router.get("/objections", response_model=List[Objection])
async def get_objections(
    category: Optional[str] = None,
    search: Optional[str] = None,
    favorites_only: bool = False
):
    """Получить список возражений с возможностью фильтрации"""
    query = {}
    
    if category:
        query["category"] = category
    
    if favorites_only:
        query["is_favorite"] = True
    
    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"responses.text": {"$regex": search, "$options": "i"}}
        ]
    
    objections = await db.objections.find(query).sort("updated_at", -1).to_list(1000)
    return [Objection(**objection) for objection in objections]

@api_router.post("/objections", response_model=Objection)
async def create_objection(objection_data: ObjectionCreate):
    """Создать новое возражение"""
    # Преобразуем список строк в список ObjectionResponse
    responses = [
        ObjectionResponse(text=response_text)
        for response_text in objection_data.responses
    ]
    
    objection = Objection(
        title=objection_data.title,
        responses=responses,
        category=objection_data.category,
        tags=objection_data.tags
    )
    
    await db.objections.insert_one(objection.dict())
    return objection

@api_router.get("/objections/{objection_id}", response_model=Objection)
async def get_objection(objection_id: str):
    """Получить конкретное возражение по ID"""
    objection = await db.objections.find_one({"id": objection_id})
    if not objection:
        raise HTTPException(status_code=404, detail="Возражение не найдено")
    return Objection(**objection)

@api_router.put("/objections/{objection_id}", response_model=Objection)
async def update_objection(objection_id: str, update_data: ObjectionUpdate):
    """Обновить возражение"""
    update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
    
    if "responses" in update_dict:
        # Преобразуем список строк в список ObjectionResponse
        update_dict["responses"] = [
            ObjectionResponse(text=response_text).dict()
            for response_text in update_dict["responses"]
        ]
    
    update_dict["updated_at"] = datetime.utcnow()
    
    result = await db.objections.update_one(
        {"id": objection_id},
        {"$set": update_dict}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Возражение не найдено")
    
    updated_objection = await db.objections.find_one({"id": objection_id})
    return Objection(**updated_objection)

@api_router.delete("/objections/{objection_id}")
async def delete_objection(objection_id: str):
    """Удалить возражение"""
    result = await db.objections.delete_one({"id": objection_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Возражение не найдено")
    return {"message": "Возражение удалено"}

@api_router.post("/objections/{objection_id}/toggle-favorite")
async def toggle_favorite(objection_id: str):
    """Переключить статус избранного для возражения"""
    objection = await db.objections.find_one({"id": objection_id})
    if not objection:
        raise HTTPException(status_code=404, detail="Возражение не найдено")
    
    new_favorite_status = not objection.get("is_favorite", False)
    
    await db.objections.update_one(
        {"id": objection_id},
        {"$set": {"is_favorite": new_favorite_status, "updated_at": datetime.utcnow()}}
    )
    
    return {"is_favorite": new_favorite_status}

@api_router.post("/objections/{objection_id}/increment-usage")
async def increment_usage_count(objection_id: str):
    """Увеличить счетчик использования возражения"""
    result = await db.objections.update_one(
        {"id": objection_id},
        {"$inc": {"usage_count": 1}, "$set": {"updated_at": datetime.utcnow()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Возражение не найдено")
    
    return {"message": "Счетчик использования увеличен"}

# Quotes endpoints
@api_router.get("/quotes", response_model=List[Quote])
async def get_quotes(category: Optional[str] = None):
    """Получить список цитат"""
    query = {}
    if category:
        query["category"] = category
    
    quotes = await db.quotes.find(query).sort("created_at", -1).to_list(1000)
    return [Quote(**quote) for quote in quotes]

@api_router.post("/quotes", response_model=Quote)
async def create_quote(quote_data: QuoteCreate):
    """Создать новую цитату"""
    quote = Quote(
        text=quote_data.text,
        author=quote_data.author,
        category=quote_data.category
    )
    
    await db.quotes.insert_one(quote.dict())
    return quote

# Search endpoint
@api_router.get("/search")
async def search_content(q: str, type: Optional[str] = None):
    """Поиск по возражениям и цитатам"""
    results = {"objections": [], "quotes": []}
    
    if not type or type == "objections":
        objections = await db.objections.find({
            "$or": [
                {"title": {"$regex": q, "$options": "i"}},
                {"responses.text": {"$regex": q, "$options": "i"}},
                {"tags": {"$regex": q, "$options": "i"}}
            ]
        }).to_list(100)
        results["objections"] = [Objection(**obj) for obj in objections]
    
    if not type or type == "quotes":
        quotes = await db.quotes.find({
            "$or": [
                {"text": {"$regex": q, "$options": "i"}},
                {"author": {"$regex": q, "$options": "i"}}
            ]
        }).to_list(100)
        results["quotes"] = [Quote(**quote) for quote in quotes]
    
    return results

# Initialize data endpoint
@api_router.post("/initialize-data")
async def initialize_data():
    """Инициализация базы данных с готовыми возражениями и цитатами"""
    # Проверяем, есть ли уже данные
    existing_objections = await db.objections.count_documents({})
    existing_quotes = await db.quotes.count_documents({})
    
    if existing_objections > 0 and existing_quotes > 0:
        return {"message": "Данные уже инициализированы", "objections": existing_objections, "quotes": existing_quotes}
    
    # Готовые возражения из оригинального кода
    initial_objections = [
        {
            "title": "Это слишком дорого.",
            "responses": [
                "Я понимаю, что цена может быть важным фактором. Давайте посмотрим, как наш продукт поможет сэкономить на обслуживании и простоях в долгосрочной перспективе.",
                "Как много стоит для вас решение этой проблемы? Наш продукт не только решает текущие задачи, но и приносит значительную экономию ресурсов.",
                "Многие наши клиенты изначально считали цену высокой, но после расчета ROI (возврата инвестиций) они увидели, что это выгодное вложение.",
                "Мы предлагаем гибкие планы оплаты, которые могут сделать покупку более доступной. Давайте обсудим варианты, которые подойдут вашему бюджету.",
                "Давайте сравним стоимость нашего продукта с аналогами на рынке. Вы увидите, что наше предложение более выгодно в долгосрочной перспективе."
            ],
            "category": "Цена",
            "tags": ["цена", "дорого", "деньги"]
        },
        {
            "title": "Мне нужно подумать.",
            "responses": [
                "Конечно, берите время. Есть ли что-то конкретное, о чем вы хотели бы узнать больше, чтобы принять решение?",
                "Прекрасно! Это значит, что вы заинтересованы. Давайте вместе обсудим ваши вопросы, чтобы вы могли принять обоснованное решение прямо сейчас.",
                "Что именно вы хотите обдумать? Может быть, я могу предоставить дополнительную информацию или ответить на ваши вопросы прямо сейчас?",
                "Когда вы планируете принять решение? Может быть, я могу отправить вам краткий обзор наших преимуществ, чтобы облегчить процесс?",
                "Многие клиенты говорят то же самое, но после того как мы разбираем детали вместе, они видят, что решение очевидно. Давайте пройдемся по ключевым моментам."
            ],
            "category": "Сомнения",
            "tags": ["подумать", "сомнения", "время"]
        },
        {
            "title": "Мы довольны текущим поставщиком.",
            "responses": [
                "Это здорово! Что вам больше всего нравится в текущем поставщике? Возможно, мы можем предложить что-то лучше или дополнительные функции.",
                "На основе того, что мы обсудили, наш продукт может сэкономить вашей компании X в 2025 году, при этом улучшив Y. Вы не получаете этого от текущего поставщика.",
                "Мы уважаем вашу лояльность, но давайте сравним, как наш продукт может дополнить или улучшить то, что вы уже используете.",
                "Многие наши клиенты были в вашей ситуации, но после перехода к нам они отметили значительное улучшение в эффективности и экономии.",
                "Давайте проведем сравнение. Какие аспекты текущего поставщика вы цените больше всего, и как мы можем предложить что-то еще более ценное?"
            ],
            "category": "Конкуренты",
            "tags": ["поставщик", "конкуренты", "лояльность"]
        },
        {
            "title": "У нас нет бюджета.",
            "responses": [
                "Я понимаю. Расскажите подробнее о ваших бюджетных ограничениях. Иногда мы можем предложить гибкие планы оплаты или приоритетные функции.",
                "Когда вы ожидаете открытия бюджета? Если это важная задача, я хотел бы связаться с вами в нужное время.",
                "Давайте рассмотрим, как наш продукт может помочь вам сэкономить или увеличить доходы, что компенсирует затраты. Например, [привести пример].",
                "Мы предлагаем опции финансирования или рассрочку платежей, чтобы сделать покупку более удобной для вашего бюджета.",
                "Многие наши клиенты изначально сталкивались с аналогичной проблемой, но после расчета экономии они нашли способ интегрировать нас в бюджет."
            ],
            "category": "Бюджет",
            "tags": ["бюджет", "деньги", "финансы"]
        },
        {
            "title": "Ваш продукт слишком сложный.",
            "responses": [
                "Понимаю, сложность может быть проблемой. Давайте упростим: наш продукт в основном делает [объясните основную выгоду], и мы предлагаем полное обучение и поддержку.",
                "Многие клиенты изначально думали так же, но после короткого обучения они оценили, как наш продукт упрощает их процессы.",
                "Мы предлагаем обширные учебные материалы и поддержку, чтобы ваша команда могла быстро освоить продукт. Давайте начнем с демонстрации.",
                "Давайте разберем ключевые функции, которые вам нужны. Вы увидите, что интерфейс интуитивен и легок в использовании.",
                "Наш продукт разработан с учетом удобства пользователя. Многие клиенты отмечают, что после первоначального обучения он становится незаменимым инструментом."
            ],
            "category": "Сложность",
            "tags": ["сложность", "обучение", "использование"]
        }
    ]
    
    # Готовые цитаты
    initial_quotes = [
        {"text": "Продажи -- это не просто процесс обмена товара на деньги. Это процесс выявления потребностей и предложения решений.", "author": "Брайан Трейси", "category": "Философия продаж"},
        {"text": "Каждый раз, когда вы говорите «да» возражению клиента, вы приближаетесь к продаже.", "author": "Джеффри Гитомер", "category": "Возражения"},
        {"text": "Люди покупают по эмоциональным причинам, а затем оправдывают покупку логическими аргументами.", "author": "Зиг Зиглар", "category": "Психология продаж"},
        {"text": "Продажи -- это не о том, чтобы убедить кого-то. Это о том, чтобы помочь кому-то принять решение.", "author": "Дэвид Сэндлер", "category": "Философия продаж"},
        {"text": "Слушайте больше, чем говорите. Никто не узнал ничего нового, слушая себя.", "author": "Фрэнк Беттджер", "category": "Коммуникация"}
    ]
    
    # Добавляем возражения
    objections_to_insert = []
    for obj_data in initial_objections:
        responses = [ObjectionResponse(text=response_text) for response_text in obj_data["responses"]]
        objection = Objection(
            title=obj_data["title"],
            responses=responses,
            category=obj_data["category"],
            tags=obj_data["tags"]
        )
        objections_to_insert.append(objection.dict())
    
    if objections_to_insert:
        await db.objections.insert_many(objections_to_insert)
    
    # Добавляем цитаты
    quotes_to_insert = []
    for quote_data in initial_quotes:
        quote = Quote(
            text=quote_data["text"],
            author=quote_data["author"],
            category=quote_data["category"]
        )
        quotes_to_insert.append(quote.dict())
    
    if quotes_to_insert:
        await db.quotes.insert_many(quotes_to_insert)
    
    return {
        "message": "Данные успешно инициализированы",
        "objections_added": len(objections_to_insert),
        "quotes_added": len(quotes_to_insert)
    }

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
