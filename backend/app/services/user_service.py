
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User


def create_user(
    db: Session,
    username: str,
    email: str,
    password: str,
) -> User:
    """创建新用户"""

    username = username.strip()
    email = email.strip().lower()

    if not username:
        raise ValueError("用户名不能为空")

    # 检查用户名是否重复
    existing_username = db.scalar(
        select(User).where(User.username == username)
    )

    if existing_username:
        raise ValueError("用户名已被注册")

    # 检查邮箱是否重复
    existing_email = db.scalar(
        select(User).where(User.email == email)
    )

    if existing_email:
        raise ValueError("邮箱已被注册")

    # 创建用户对象
    user = User(
        username=username,
        email=email,
        password_hash=hash_password(password),
        is_active=True,
    )

    db.add(user)

    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise ValueError("用户名或邮箱已被注册")

    return user

def authenticate_user(
    db: Session,
    username_or_email: str,
    password: str,
):
    """验证用户登录信息"""

    identifier = username_or_email.strip()

    # 支持用户名或邮箱登录
    user = db.scalar(
        select(User).where(
            (User.username == identifier)
            | (User.email == identifier.lower())
        )
    )

    # 账号不存在或账号已停用
    if user is None or not user.is_active:
        return None

    # 验证密码
    if not verify_password(password, user.password_hash):
        return None

    return user
