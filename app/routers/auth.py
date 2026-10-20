import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas import UserRegisterRequest, UserLoginRequest, AuthResponse, UserProfile, SimpleMessageResponse
from app.auth import get_current_user, create_jwt_token
from app.database import db

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(req: UserRegisterRequest):
    """
    สมัครสมาชิกผู้ใช้ใหม่ (Role: user)
    """
    # 1. Supabase Auth if connected
    if db.is_supabase_connected and db.client:
        try:
            user = None
            # Use admin API with auto-confirmed email so users can login immediately
            try:
                created = db.client.auth.admin.create_user({
                    "email": req.email,
                    "password": req.password,
                    "email_confirm": True,
                    "user_metadata": {
                        "full_name": req.full_name,
                        "phone_number": req.phone_number,
                        "role": "user"
                    }
                })
                user = created.user if hasattr(created, "user") else created
            except Exception as admin_err:
                err_msg = str(admin_err).lower()
                if "already registered" in err_msg or "already exists" in err_msg or "unique" in err_msg:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="อีเมลนี้ถูกใช้งานในระบบแล้ว"
                    )
                # Fallback to standard sign_up
                res = db.client.auth.sign_up({
                    "email": req.email,
                    "password": req.password,
                    "options": {
                        "data": {
                            "full_name": req.full_name,
                            "phone_number": req.phone_number,
                            "role": "user"
                        }
                    }
                })
                user = res.user

            if not user:
                raise HTTPException(status_code=400, detail="ไม่สามารถสร้างผู้ใช้งานได้")

            # Ensure profile row exists in public.profiles
            try:
                db.client.table("profiles").upsert({
                    "id": user.id,
                    "full_name": req.full_name,
                    "phone_number": req.phone_number,
                    "role": "user"
                }).execute()
            except Exception as pe:
                print(f"[Profiles Upsert Warning] {pe}")

            # Obtain session token
            token = None
            try:
                login_res = db.client.auth.sign_in_with_password({
                    "email": req.email,
                    "password": req.password
                })
                if login_res and login_res.session:
                    token = login_res.session.access_token
            except Exception:
                pass

            if not token:
                token = create_jwt_token({
                    "sub": user.id,
                    "email": req.email,
                    "role": "user"
                })

            profile_data = {
                "id": user.id,
                "email": req.email,
                "full_name": req.full_name,
                "phone_number": req.phone_number,
                "role": "user",
                "created_at": datetime.now(timezone.utc)
            }
            return {
                "access_token": token,
                "token_type": "bearer",
                "user": {"id": user.id, "email": req.email},
                "profile": profile_data
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Registration failed: {str(e)}"
            )

    # 2. Local fallback registration
    for p in db._profiles.values():
        if p.get("email") == req.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="อีเมลนี้ถูกใช้งานในระบบแล้ว"
            )

    user_id = str(uuid.uuid4())
    profile_record = {
        "id": user_id,
        "email": req.email,
        "full_name": req.full_name,
        "phone_number": req.phone_number,
        "role": "user",
        "password_hash": req.password, # For local demo
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    db._profiles[user_id] = profile_record

    token = create_jwt_token({
        "sub": user_id,
        "email": req.email,
        "role": "user"
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": user_id, "email": req.email},
        "profile": {
            "id": user_id,
            "email": req.email,
            "full_name": req.full_name,
            "phone_number": req.phone_number,
            "role": "user",
            "created_at": datetime.fromisoformat(profile_record["created_at"])
        }
    }

@router.post("/login", response_model=AuthResponse)
def login(req: UserLoginRequest):
    """
    เข้าสู่ระบบสำหรับลูกค้าและผู้ดูแลระบบ
    """
    if db.is_supabase_connected and db.client:
        try:
            res = db.client.auth.sign_in_with_password({
                "email": req.email,
                "password": req.password
            })
            if res.user and res.session:
                user = res.user
                profile_res = db.client.table("profiles").select("*").eq("id", user.id).execute()
                profile_db = profile_res.data[0] if profile_res.data else {}
                role = profile_db.get("role", "user")

                return {
                    "access_token": res.session.access_token,
                    "token_type": "bearer",
                    "user": {"id": user.id, "email": user.email},
                    "profile": {
                        "id": user.id,
                        "email": user.email,
                        "full_name": profile_db.get("full_name") or user.user_metadata.get("full_name"),
                        "phone_number": profile_db.get("phone_number") or user.user_metadata.get("phone_number"),
                        "role": role,
                        "created_at": user.created_at
                    }
                }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="อีเมลหรือรหัสผ่านไม่ถูกต้อง"
            )

    # Local fallback verification
    matched_profile = None
    for p in db._profiles.values():
        if p.get("email") == req.email and p.get("password_hash") == req.password:
            matched_profile = p
            break

    if not matched_profile:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="อีเมลหรือรหัสผ่านไม่ถูกต้อง"
        )

    token = create_jwt_token({
        "sub": matched_profile["id"],
        "email": matched_profile["email"],
        "role": matched_profile["role"]
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": matched_profile["id"], "email": matched_profile["email"]},
        "profile": {
            "id": matched_profile["id"],
            "email": matched_profile["email"],
            "full_name": matched_profile.get("full_name"),
            "phone_number": matched_profile.get("phone_number"),
            "role": matched_profile.get("role", "user"),
            "created_at": datetime.fromisoformat(matched_profile["created_at"])
        }
    }

@router.post("/logout", response_model=SimpleMessageResponse)
def logout(current_user: dict = Depends(get_current_user)):
    """
    ออกจากระบบ
    """
    if db.is_supabase_connected and db.client:
        try:
            db.client.auth.sign_out()
        except Exception:
            pass
    return {"success": True, "message": "ออกจากระบบสำเร็จ"}

@router.get("/me", response_model=UserProfile)
def get_me(current_user: dict = Depends(get_current_user)):
    """
    ดูข้อมูลโปรไฟล์และ Role ของบัญชีปัจจุบัน
    """
    return {
        "id": current_user["id"],
        "email": current_user.get("email"),
        "full_name": current_user.get("full_name"),
        "phone_number": current_user.get("phone_number"),
        "role": current_user.get("role", "user"),
        "created_at": datetime.now(timezone.utc)
    }
