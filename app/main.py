import string
import random
from datetime import datetime, timezone
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.models import Link, LinkAnalytics
from app.schemas import LinkCreate, LinkResponse, LinkUpdate, LinkStatsResponse

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="URL Shortener",
    description="Сервис для сокращения ссылок",
    version="1.0.0"
)

analytics = LinkAnalytics()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def generate_short_code(length: int = 6):
    """Генерирует уникальный короткий код."""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


def get_link_by_code(db: Session, short_code: str):
    """Находит ссылку по короткому коду."""
    return db.query(Link).filter(Link.short_code == short_code).first()


def get_link_by_url(db: Session, original_url: str):
    """Находит ссылку по оригинальному URL."""
    return db.query(Link).filter(Link.original_url == original_url).first()


@app.post("/links/shorten", response_model=LinkResponse, status_code=status.HTTP_201_CREATED)
def create_short_link(link_data: LinkCreate, db: Session = Depends(get_db)):
    """
    Создает короткую ссылку.
    Если предоставлен `custom_alias`, используется он.
    Если нет, генерируется случайный.
    """
    if link_data.custom_alias:
        # Проверяем уникальность кастомного алиаса
        existing_link = get_link_by_code(db, link_data.custom_alias)
        if existing_link:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Кастомный алиас уже существует."
            )
        short_code = link_data.custom_alias
    else:
        # Генерируем уникальный код
        short_code = generate_short_code()
        while get_link_by_code(db, short_code):
            short_code = generate_short_code()

    db_link = Link(
        short_code=short_code,
        original_url=str(link_data.original_url),
        created_at=datetime.now(timezone.utc)
    )
    db.add(db_link)
    db.commit()
    db.refresh(db_link)

    analytics.stats[short_code] = {'clicks': 0, 'last_used': None}

    return db_link


@app.get("/{short_code}", response_class=RedirectResponse)
def redirect_to_original_url(short_code: str, db: Session = Depends(get_db)):
    """
    Перенаправляет пользователя на оригинальный URL.
    """
    link = get_link_by_code(db, short_code)
    if not link:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ссылка не найдена.")
    if short_code in analytics.stats:
        analytics.stats[short_code]['clicks'] += 1
        analytics.stats[short_code]['last_used'] = datetime.now(timezone.utc)

    return RedirectResponse(url=link.original_url)


@app.get("/links/search", response_model=LinkResponse)
def search_link_by_url(original_url: str, db: Session = Depends(get_db)):
    """
    Находит короткую ссылку по оригинальному URL.
    """
    link = get_link_by_url(db, original_url)
    if not link:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ссылка не найдена.")
    
    return link


@app.get("/links/{short_code}/stats", response_model=LinkStatsResponse)
def get_link_stats(short_code: str, db: Session = Depends(get_db)):
    """
    Получает статистику по короткой ссылке.
    """
    link = get_link_by_code(db, short_code)
    if not link:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ссылка не найдена.")
    stats = analytics.stats.get(short_code, {'clicks': 0, 'last_used': None})

    return LinkStatsResponse(
        original_url=link.original_url,
        created_at=link.created_at,
        clicks=stats['clicks'],
        last_used=stats['last_used']
    )


@app.put("/links/{short_code}", response_model=LinkResponse)
def update_link(short_code: str, link_update: LinkUpdate, db: Session = Depends(get_db)):
    """
    Обновляет оригинальный URL, привязанный к короткой ссылке.
    """
    link = get_link_by_code(db, short_code)
    if not link:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ссылка не найдена.")
    
    link.original_url = str(link_update.original_url)
    db.commit()
    db.refresh(link)
    
    return link


@app.delete("/links/{short_code}", status_code=status.HTTP_204_NO_CONTENT)
def delete_link(short_code: str, db: Session = Depends(get_db)):
    """
    Удаляет короткую ссылку.
    """
    link = get_link_by_code(db, short_code)
    if not link:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ссылка не найдена.")
    
    db.delete(link)
    db.commit()
    
    if short_code in analytics.stats:
        del analytics.stats[short_code]
    
    return None