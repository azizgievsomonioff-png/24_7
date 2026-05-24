from aiogram.fsm.state import State, StatesGroup


class CardStates(StatesGroup):
    choose_marketplace = State()
    choose_category = State()
    custom_category = State()
    upload_photo = State()
    product_name = State()
    target_audience = State()
    custom_audience = State()
    main_advantage = State()
    material = State()
    color = State()
    size_or_complect = State()
    use_cases = State()
    customer_pains = State()
    key_features = State()
    confirm_generation = State()
    show_result = State()


class SeoStates(StatesGroup):
    waiting_query = State()


class PromptStates(StatesGroup):
    waiting_description = State()


class ChatGptPromptStates(StatesGroup):
    waiting_slide_correction = State()
