import asyncio
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.order import Order
from app.models.user import User
from app.schemas.order import DashboardStats, OCRResponse, OrderCreate, OrderList, OrderOut, OrderUpdate
from app.services.file_store import move_to_order, save_upload, upload_path
from app.services.ocr import run_ocr

router = APIRouter(prefix="/orders", tags=["orders"])


def serialize(order: Order) -> dict:
    return {
        "id": str(order.id),
        "order_number": order.order_number,
        "customer_name": order.customer_name,
        "order_date": order.order_date,
        "total_amount": order.total_amount,
        "currency": order.currency,
        "status": order.status,
        "notes": order.notes,
        "source_filename": order.source_filename,
        "raw_text": order.raw_text,
        "extracted_data": order.extracted_data,
        "created_at": order.created_at,
        "updated_at": order.updated_at,
        "owner": {"id": str(order.owner.id), "email": order.owner.email, "name": order.owner.name},
    }


def scoped_query(user: User):
    query = select(Order).where(Order.deleted_at.is_(None))
    return query if user.role == "admin" else query.where(Order.owner_id == user.id)


@router.post("/ocr", response_model=OCRResponse)
async def recognize_order(
    file: UploadFile = File(...), user: User = Depends(get_current_user)
):
    token, path = await save_upload(file)
    try:
        result = await asyncio.to_thread(run_ocr, path)
    except Exception as exc:
        path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"OCR 辨識失敗：{exc}") from exc
    return OCRResponse(upload_token=token, filename=file.filename or path.name, **result)


@router.post("", response_model=OrderOut, status_code=201)
async def create_order(
    payload: OrderCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    source = upload_path(payload.upload_token)
    order = Order(
        owner_id=user.id,
        order_number=payload.order_number.strip(),
        customer_name=payload.customer_name.strip(),
        order_date=payload.order_date,
        total_amount=payload.total_amount,
        currency=payload.currency.upper(),
        notes=payload.notes,
        source_filename=payload.source_filename,
        source_path="",
        raw_text=payload.raw_text,
        extracted_data=payload.extracted_data,
    )
    db.add(order)
    await db.flush()
    target = move_to_order(source, str(order.id))
    order.source_path = str(target)
    await db.commit()
    result = await db.scalar(
        select(Order).where(Order.id == order.id).options(selectinload(Order.owner))
    )
    return serialize(result)


@router.get("", response_model=OrderList)
async def list_orders(
    q: str = "",
    status: str = "",
    date_from: date | None = None,
    date_to: date | None = None,
    owner_id: uuid.UUID | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = scoped_query(user)
    if q:
        needle = f"%{q}%"
        query = query.where(or_(Order.order_number.ilike(needle), Order.customer_name.ilike(needle)))
    if status:
        query = query.where(Order.status == status)
    if date_from:
        query = query.where(Order.order_date >= date_from)
    if date_to:
        query = query.where(Order.order_date <= date_to)
    if owner_id and user.role == "admin":
        query = query.where(Order.owner_id == owner_id)
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0
    rows = await db.scalars(
        query.options(selectinload(Order.owner))
        .order_by(Order.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return OrderList(
        items=[serialize(order) for order in rows.all()], total=total, page=page, page_size=page_size
    )


@router.get("/stats", response_model=DashboardStats)
async def stats(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    base = [Order.deleted_at.is_(None)]
    if user.role != "admin":
        base.append(Order.owner_id == user.id)
    today = date.today()
    month_start = datetime(today.year, today.month, 1, tzinfo=timezone.utc)
    total = await db.scalar(select(func.count(Order.id)).where(*base)) or 0
    this_month = await db.scalar(
        select(func.count(Order.id)).where(*base, Order.created_at >= month_start)
    ) or 0
    amount = await db.scalar(select(func.coalesce(func.sum(Order.total_amount), 0)).where(*base))
    pending = await db.scalar(
        select(func.count(Order.id)).where(*base, Order.status == "pending")
    ) or 0
    return DashboardStats(
        total_orders=total,
        this_month=this_month,
        total_amount=Decimal(amount or 0),
        pending_review=pending,
    )


async def get_scoped_order(order_id: uuid.UUID, user: User, db: AsyncSession) -> Order:
    query = scoped_query(user).where(Order.id == order_id).options(selectinload(Order.owner))
    order = await db.scalar(query)
    if not order:
        raise HTTPException(status_code=404, detail="找不到訂單")
    return order


@router.get("/{order_id}", response_model=OrderOut)
async def get_order(
    order_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return serialize(await get_scoped_order(order_id, user, db))


@router.patch("/{order_id}", response_model=OrderOut)
async def update_order(
    order_id: uuid.UUID,
    payload: OrderUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    order = await get_scoped_order(order_id, user, db)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(order, key, value)
    await db.commit()
    await db.refresh(order)
    return serialize(order)


@router.delete("/{order_id}", status_code=204)
async def delete_order(
    order_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    order = await get_scoped_order(order_id, user, db)
    order.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    return Response(status_code=204)
