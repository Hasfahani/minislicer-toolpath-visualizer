# Purpose: Supplies reusable Streamlit authentication and role checks.
# Reason: Company operations must not rely on anonymous browser access.
"""Authentication helpers for MiniSlicer's operational Streamlit pages."""

from __future__ import annotations

import os
from typing import Iterable

import streamlit as st

from src.company_store import CompanyStore, User

SESSION_USER_KEY = "_minislicer_user"


def current_user() -> User | None:
    payload = st.session_state.get(SESSION_USER_KEY)
    if not isinstance(payload, dict):
        return None
    return User(
        username=str(payload["username"]),
        role=str(payload["role"]),
        active=bool(payload.get("active", True)),
    )


def require_user(
    store: CompanyStore,
    *,
    roles: Iterable[str] | None = None,
) -> User:
    """Render first-run setup/login and stop until an authorized user exists."""
    if not store.has_users():
        st.subheader("Initialize company workspace")
        st.info("Create the first administrator. This form disappears after setup.")
        with st.form("bootstrap-admin"):
            username = st.text_input("Administrator username")
            password = st.text_input("Administrator password", type="password")
            confirmation = st.text_input("Confirm password", type="password")
            submitted = st.form_submit_button("Create administrator", type="primary")
        if submitted:
            if password != confirmation:
                st.error("Passwords do not match.")
            else:
                try:
                    user = store.create_user(
                        username,
                        password,
                        "admin",
                        actor="system.bootstrap",
                    )
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.session_state[SESSION_USER_KEY] = {
                        "username": user.username,
                        "role": user.role,
                        "active": user.active,
                    }
                    st.rerun()
        st.stop()

    user = current_user()
    if user is None:
        st.subheader("Company sign in")
        with st.form("company-login"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in", type="primary")
        if submitted:
            authenticated = store.authenticate(username, password)
            if authenticated is None:
                st.error("Invalid username or password.")
            else:
                st.session_state[SESSION_USER_KEY] = {
                    "username": authenticated.username,
                    "role": authenticated.role,
                    "active": authenticated.active,
                }
                st.rerun()
        st.stop()

    allowed = set(roles or ())
    if allowed and user.role not in allowed:
        st.error("Your role does not permit this operation.")
        st.stop()

    with st.sidebar:
        st.caption(f"Signed in as **{user.username}** ({user.role})")
        if st.button("Sign out"):
            st.session_state.pop(SESSION_USER_KEY, None)
            st.rerun()
    return user


def can_review(user: User) -> bool:
    return user.role in {"admin", "engineer"}


def is_admin(user: User) -> bool:
    return user.role == "admin"


def global_auth_required() -> bool:
    return os.getenv("MINISLICER_AUTH_REQUIRED", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def require_global_access_if_configured() -> User | None:
    """Protect ordinary planner/tutorial pages in company deployments."""
    if not global_auth_required():
        return None
    return require_user(CompanyStore())
