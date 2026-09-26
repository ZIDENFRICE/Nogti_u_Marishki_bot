from aiogram import Router, F
from aiogram.types import CallbackQuery, Message

from database.db import accept_terms
from keyboards.user_kb import docs_menu_kb, doc_view_kb
from utils.legal import (
    OFFER_TEXT, PRIVACY_TEXT, CONSENT_PD_TEXT, DOCS_MENU_TEXT,
)
from utils.safe_edit import safe_edit

router = Router()


@router.callback_query(F.data == "docs_menu")
async def docs_menu(call: CallbackQuery):
    await safe_edit(call, DOCS_MENU_TEXT, reply_markup=docs_menu_kb())


@router.callback_query(F.data == "doc_offer")
async def show_offer(call: CallbackQuery):
    await safe_edit(call, OFFER_TEXT, reply_markup=doc_view_kb())


@router.callback_query(F.data == "doc_privacy")
async def show_privacy(call: CallbackQuery):
    await safe_edit(call, PRIVACY_TEXT, reply_markup=doc_view_kb())


@router.callback_query(F.data == "doc_consent")
async def show_consent(call: CallbackQuery):
    await safe_edit(call, CONSENT_PD_TEXT, reply_markup=doc_view_kb())


@router.callback_query(F.data == "legal_agree")
async def legal_agree(call: CallbackQuery):
    await accept_terms(call.from_user.id)
    await call.answer("✅ Спасибо!")


@router.message(F.text == "/docs")
async def cmd_docs(message: Message):
    await message.answer(DOCS_MENU_TEXT, reply_markup=docs_menu_kb())