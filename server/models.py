
from sqlalchemy.orm import validates
from sqlalchemy.ext.hybrid import hybrid_property
from marshmallow import Schema, fields

from config import db, bcrypt


class User(db.Model):
    """Represent application users and their authentication information"""

    __tablename__ = 'users'

    # User database columns
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, nullable=False, unique=True)
    _password_hash = db.Column(db.String)
    image_url = db.Column(db.String)
    bio = db.Column(db.String)

    # Establish a one-to-many relationship with recipes
    recipes = db.relationship('Recipe', back_populates='user')

    @hybrid_property
    def password_hash(self):
        """Prevent direct access to stored password hashes"""

        raise AttributeError("Password hashes may not be viewed")

    @password_hash.setter
    def password_hash(self, password):
        """Generate and store a bcrypt hash of the provided password"""

        # Generate a secure password hash using bcrypt
        hashed_password = bcrypt.generate_password_hash(password)

        # Convert the generated hash from bytes to a UTF-8 string
        decoded_hashed_password = hashed_password.decode("utf-8")

        # Store the encoded hash rather than the original password
        self._password_hash = decoded_hashed_password

    @validates('username')
    def validate_username(self, key, username):
        """Ensure usernames are non-empty strings"""

        # Reject usernames that are not strings
        if not isinstance(username, str):
            raise ValueError("Username must be a string")

        # Reject empty or whitespace-only usernames
        if not username.strip():
            raise ValueError("Username must be present")

        return username

    def authenticate(self, password):
        """Verify a password against the user's stored bcrypt hash"""

        return bcrypt.check_password_hash(self._password_hash, password)

    def __repr__(self):
        """Return a readable representation of the user"""

        return f'User {self.username}, ID: {self.id}'


class Recipe(db.Model):
    """Represent recipes created by application users"""

    __tablename__ = 'recipes'

    # Recipe database columns
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, nullable=False)
    instructions = db.Column(db.String, nullable=False)
    minutes_to_complete = db.Column(db.Integer, nullable=False)

    # Establish a many-to-one relationship with the User model
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    user = db.relationship('User', back_populates='recipes')

    @validates('minutes_to_complete')
    def validate_minutes(self, key, minutes):
        """Ensure recipe completion time is a positive integer"""

        # Reject values that are not integers
        if type(minutes) is not int:
            raise ValueError("Minutes must be an integer")

        # Reject zero or negative completion times
        if minutes <= 0:
            raise ValueError("Minutes must be greater than 0")

        return minutes

    @validates('title')
    def validate_title(self, key, title):
        """Ensure recipe titles contain non-whitespace text"""

        # Reject titles that are not strings
        if not isinstance(title, str):
            raise ValueError("Title must be a string")

        # Reject empty or whitespace-only titles
        if not title.strip():
            raise ValueError("Title must be present")

        return title

    @validates('instructions')
    def validate_instructions(self, key, instructions):
        """Ensure recipe instructions contain at least 50 characters"""

        # Reject instructions that are not strings
        if not isinstance(instructions, str):
            raise ValueError("Instructions must be a string")

        # Reject empty or whitespace-only instructions
        if not instructions.strip():
            raise ValueError("Instructions must be present")

        # Enforce the minimum instruction length after trimming whitespace
        if len(instructions.strip()) < 50:
            raise ValueError("Instructions must be at least 50 characters")

        return instructions

    # Enforce positive completion times at the database level
    __table_args__ = (
        db.CheckConstraint(
            'minutes_to_complete > 0',
            name='check_positive_minutes'
        ),
    )


class UserSchema(Schema):
    """Serialize user information without exposing password hashes"""

    # Exclude the database ID from deserialization
    id = fields.Int(dump_only=True)

    # Public user profile fields
    username = fields.String()
    image_url = fields.String()
    bio = fields.String()


class RecipeSchema(Schema):
    """Serialize recipe information and its associated user"""

    # Exclude the database ID from deserialization
    id = fields.Int(dump_only=True)

    # Recipe information fields
    title = fields.String()
    instructions = fields.String()
    minutes_to_complete = fields.Int()

    # Include the recipe author's serialized user information
    user = fields.Nested(UserSchema)
