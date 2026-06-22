"""Locale-keyed IVR prompt templates (P3-009).

Architecture only -- this module has exactly one populated locale (English).
Adding a second locale means adding one more dict entry to `_PROMPTS`; no
step-handler logic in `ivr_service.py` changes, because every call site
already goes through `resolve_prompt()`/`format_option_list()` with an
explicit `locale` argument rather than an inline string literal.

`resolve_prompt()` falls back to `IVR_DEFAULT_LOCALE` whenever the requested
locale is missing entirely, or is missing a specific key (so a partially
translated locale degrades gracefully instead of raising or showing a blank
prompt).
"""
from enum import StrEnum
from typing import Sequence

IVR_DEFAULT_LOCALE = "en"


class PromptKey(StrEnum):
    SESSION_EXPIRED = "session_expired"
    SESSION_ALREADY_COMPLETE = "session_already_complete"
    UNEXPECTED_STATE = "unexpected_state"
    TOO_MANY_INVALID_KEYS = "too_many_invalid_keys"
    TOO_MANY_NO_INPUT = "too_many_no_input"
    NO_INPUT_PREFIX = "no_input_prefix"
    NO_SLOTS = "no_slots"
    NO_SERVICES = "no_services"
    PLEASE_MAKE_A_SELECTION = "please_make_a_selection"
    MAIN_MENU_INTERNAL = "main_menu_internal"
    MAIN_MENU_EXTERNAL = "main_menu_external"
    GREETING_PREFIX = "greeting_prefix"
    SELECT_SERVICE = "select_service"
    INVALID_SELECT_SERVICE = "invalid_select_service"
    NO_SLOTS_FOR_SERVICE = "no_slots_for_service"
    AVAILABLE_SLOTS_FOR_SERVICE = "available_slots_for_service"
    SELECT_SLOT = "select_slot"
    INVALID_SELECT_SLOT = "invalid_select_slot"
    BOOKING_CONFIRMED = "booking_confirmed"
    STAFF_SELECTION_PROMPT = "staff_selection_prompt"
    EXTERNAL_LINK_SENT = "external_link_sent"
    TRANSFER_DISABLED = "transfer_disabled"
    TRANSFER_NO_STAFF = "transfer_no_staff"
    TRANSFERRING = "transferring"
    PRESS_1_MAIN_MENU = "press_1_main_menu"
    NO_UPCOMING_BOOKING_PREFIX = "no_upcoming_booking_prefix"
    MANAGE_BOOKING_FOUND = "manage_booking_found"
    BOOKING_CANCELLED = "booking_cancelled"
    NO_SLOTS_TO_RESCHEDULE = "no_slots_to_reschedule"
    SELECT_NEW_TIME = "select_new_time"
    INVALID_SELECT_NEW_TIME = "invalid_select_new_time"
    BOOKING_RESCHEDULED = "booking_rescheduled"

    OPTION_ITEM = "option_item"
    STAFF_OPTION_PREFERRED = "staff_option_preferred"
    STAFF_OPTION_ANY = "staff_option_any"

    LABEL_MAIN_MENU = "label_main_menu"
    LABEL_BOOK_APPOINTMENT = "label_book_appointment"
    LABEL_BOOKING_LINK_SMS = "label_booking_link_sms"
    LABEL_SPEAK_WITH_STAFF = "label_speak_with_staff"
    LABEL_MANAGE_BOOKING = "label_manage_booking"
    LABEL_CANCEL_APPOINTMENT = "label_cancel_appointment"
    LABEL_RESCHEDULE_APPOINTMENT = "label_reschedule_appointment"
    LABEL_ANY_AVAILABLE_STAFF = "label_any_available_staff"


_PROMPTS: dict[str, dict[PromptKey, str]] = {
    "en": {
        PromptKey.SESSION_EXPIRED: "Your session has expired. Please call again to book an appointment.",
        PromptKey.SESSION_ALREADY_COMPLETE: "This session is already complete. Please call again.",
        PromptKey.UNEXPECTED_STATE: "Unexpected session state.",
        PromptKey.TOO_MANY_INVALID_KEYS: (
            "Too many invalid inputs. Your session has ended. "
            "Please call again to book an appointment."
        ),
        PromptKey.TOO_MANY_NO_INPUT: (
            "We didn't receive any input. Your session has ended. "
            "Please call again to book an appointment."
        ),
        PromptKey.NO_INPUT_PREFIX: "We didn't hear a response. ",
        PromptKey.NO_SLOTS: "No slots are available. Please call back later.",
        PromptKey.NO_SERVICES: "Sorry, no services are currently available. Please call back later.",
        PromptKey.PLEASE_MAKE_A_SELECTION: "Please make a selection.",
        PromptKey.MAIN_MENU_INTERNAL: (
            "Welcome! Press 1 to book an appointment, "
            "press 2 to speak with a staff member, "
            "or press 3 to manage an existing appointment."
        ),
        PromptKey.MAIN_MENU_EXTERNAL: (
            "Welcome! Press 1 to receive a booking link by SMS, "
            "press 2 to speak with a staff member, "
            "or press 3 to manage an existing appointment."
        ),
        PromptKey.GREETING_PREFIX: "Welcome back, {name}! ",
        PromptKey.SELECT_SERVICE: "Please select a service: {options}.",
        PromptKey.INVALID_SELECT_SERVICE: "Invalid choice. Please select a service: {options}.",
        PromptKey.NO_SLOTS_FOR_SERVICE: (
            "Sorry, there are no available slots for {service_name} "
            "in the next week. Please call back later."
        ),
        PromptKey.AVAILABLE_SLOTS_FOR_SERVICE: (
            "Available slots for {service_name}: {options}. Press your choice."
        ),
        PromptKey.SELECT_SLOT: "Please select a slot: {options}.",
        PromptKey.INVALID_SELECT_SLOT: "Invalid choice. Please select a slot: {options}.",
        PromptKey.BOOKING_CONFIRMED: (
            "Your appointment has been booked for {when}. "
            "You will receive an SMS confirmation. Thank you, goodbye!"
        ),
        PromptKey.STAFF_SELECTION_PROMPT: "Who would you like to book your {service_name} with? {options}.",
        PromptKey.EXTERNAL_LINK_SENT: (
            "We have sent you an SMS with a link to book your appointment online. "
            "Thank you, goodbye!"
        ),
        PromptKey.TRANSFER_DISABLED: (
            "Transfer to staff is not available for this business. Press 1 to book an appointment."
        ),
        PromptKey.TRANSFER_NO_STAFF: (
            "Sorry, no staff members are available to take your call right now. "
            "Press 1 to book an appointment."
        ),
        PromptKey.TRANSFERRING: "Transferring you to a staff member. Please hold.",
        PromptKey.PRESS_1_MAIN_MENU: "Press 1 to go back to the main menu.",
        PromptKey.NO_UPCOMING_BOOKING_PREFIX: "We couldn't find an upcoming appointment for this number. ",
        PromptKey.MANAGE_BOOKING_FOUND: (
            "We found your {service_name} appointment for {when}. "
            "Press 1 to cancel it, press 2 to reschedule it, or press 3 to go back to the main menu."
        ),
        PromptKey.BOOKING_CANCELLED: "Your appointment has been cancelled. Thank you, goodbye!",
        PromptKey.NO_SLOTS_TO_RESCHEDULE: (
            "Sorry, there are no available slots to reschedule into right now. Please call back later."
        ),
        PromptKey.SELECT_NEW_TIME: "Please select a new time: {options}.",
        PromptKey.INVALID_SELECT_NEW_TIME: "Invalid choice. Please select a new time: {options}.",
        PromptKey.BOOKING_RESCHEDULED: (
            "Your appointment has been rescheduled to {when}. "
            "You will receive an SMS confirmation. Thank you, goodbye!"
        ),
        PromptKey.OPTION_ITEM: "press {key} for {label}",
        PromptKey.STAFF_OPTION_PREFERRED: "press {key} for {label}, who you saw last time",
        PromptKey.STAFF_OPTION_ANY: "press 0 for any available staff member",
        PromptKey.LABEL_MAIN_MENU: "Main menu",
        PromptKey.LABEL_BOOK_APPOINTMENT: "Book an appointment",
        PromptKey.LABEL_BOOKING_LINK_SMS: "Receive a booking link by SMS",
        PromptKey.LABEL_SPEAK_WITH_STAFF: "Speak with staff",
        PromptKey.LABEL_MANAGE_BOOKING: "Manage an existing appointment",
        PromptKey.LABEL_CANCEL_APPOINTMENT: "Cancel appointment",
        PromptKey.LABEL_RESCHEDULE_APPOINTMENT: "Reschedule appointment",
        PromptKey.LABEL_ANY_AVAILABLE_STAFF: "Any available staff member",
    },
}


def resolve_prompt(
    prompt_key: PromptKey, *, locale: str = IVR_DEFAULT_LOCALE, **kwargs: object
) -> str:
    """Look up `prompt_key`'s template for `locale`, falling back to
    IVR_DEFAULT_LOCALE if the locale is unknown or doesn't have that key
    (a partially translated locale degrades gracefully instead of raising
    or returning a blank prompt), then interpolate `kwargs`."""
    locale_table = _PROMPTS.get(locale, _PROMPTS[IVR_DEFAULT_LOCALE])
    template = locale_table.get(prompt_key) or _PROMPTS[IVR_DEFAULT_LOCALE][prompt_key]
    return template.format(**kwargs)


def format_option_list(options: Sequence, *, locale: str = IVR_DEFAULT_LOCALE) -> str:
    """Join an IvrOption sequence into "press 1 for X, press 2 for Y" using
    the locale's OPTION_ITEM template, so the join phrase itself is
    translatable rather than hardcoded at every step-handler call site."""
    return ", ".join(
        resolve_prompt(PromptKey.OPTION_ITEM, locale=locale, key=o.key, label=o.label)
        for o in options
    )
