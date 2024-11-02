from dataclasses import dataclass
from typing import Optional, List

@dataclass
class User:
    doc_id: str
    email: str
    name: str
    picture: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            doc_id=data.get('doc_id'),
            email=data.get('email'),
            name=data.get('name'),
            picture=data.get('picture')
        )

    def to_dict(self):
        return {
            'doc_id': self.doc_id,
            'email': self.email,
            'name': self.name,
            'picture': self.picture
        }

    def __init__(self, doc_id, email, name, picture=None):  # Add picture parameter
        self.doc_id = doc_id
        self.email = email
        self.name = name
        self.picture = picture  # Store the picture URL

@dataclass
class QRCode:
    id: str
    user_id: str
    link: str
    file_id: str

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=data.get('$id') or data.get('id'),
            user_id=data.get('user_id'),
            link=data.get('link'),
            file_id=data.get('file_id')
        )

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'link': self.link,
            'file_id': self.file_id
        }

@dataclass
class UserWithQRCodes:
    user: User
    qr_codes: List[QRCode]

    @classmethod
    def from_dict(cls, user_data: dict, qr_codes_data: List[dict]):
        user = User.from_dict(user_data)
        qr_codes = [QRCode.from_dict(qr_code) for qr_code in qr_codes_data]
        return cls(user=user, qr_codes=qr_codes)

    def to_dict(self):
        return {
            'user': self.user.to_dict(),
            'qr_codes': [qr_code.to_dict() for qr_code in self.qr_codes]
        }
