
#!/usr/bin/env python3

from flask import request, session
from flask_restful import Resource
from sqlalchemy.exc import IntegrityError

from config import app, db, api
from models import User, Recipe, UserSchema, RecipeSchema


class Signup(Resource):
    """Handle user registration and account creation"""

    def post(self):
        """Register a new user and establish an authenticated session"""

        # Retrieve registration information from the request
        data = request.get_json()

        username = data.get("username")
        password = data.get("password")
        image_url = data.get("image_url")
        bio = data.get("bio")

        try:
            # Validate that a non-empty password was provided
            if not isinstance(password, str) or not password.strip():
                raise ValueError("Password must be a non-empty string")

            # Create a new user with the provided profile information
            new_user = User(
                username=username,
                image_url=image_url,
                bio=bio
            )

            # Hash the password using the User model's property setter
            new_user.password_hash = password

            # Save the new user to the database
            db.session.add(new_user)
            db.session.commit()

            # Authenticate the newly registered user
            session["user_id"] = new_user.id

            # Serialize the user without exposing the password hash
            user_json = UserSchema().dump(new_user)

            return user_json, 201

        except IntegrityError:
            # Roll back database changes if a constraint is violated
            db.session.rollback()
            return {"message": "Username already exists"}, 422

        except ValueError as error:
            # Return validation errors without saving the user
            db.session.rollback()
            return {"message": str(error)}, 422


class CheckSession(Resource):
    """Verify whether a user has an active authenticated session"""

    def get(self):
        """Return the authenticated user or an unauthorized response"""

        # Retrieve the user ID stored in the session
        user_id = session.get('user_id')

        if user_id:
            # Look up the user associated with the active session
            user = User.query.filter(User.id == user_id).first()

            if user:
                # Return the authenticated user's serialized information
                return UserSchema().dump(user), 200

        # Reject requests without a valid authenticated user
        return {"message": "Unauthorized access"}, 401


class Login(Resource):
    """Handle user authentication"""

    def post(self):
        """Authenticate a user using their username and password"""

        # Retrieve login credentials from the request
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        # Find the user associated with the provided username
        user = User.query.filter(User.username == username).first()

        # Verify the password against the stored password hash
        if user and user.authenticate(password):

            # Store the authenticated user's ID in the session
            session['user_id'] = user.id

            # Return the authenticated user's serialized information
            return UserSchema().dump(user), 200

        # Reject invalid login credentials
        return {'message': 'Invalid username or password'}, 401


class Logout(Resource):
    """Handle termination of authenticated user sessions"""

    def delete(self):
        """Remove the authenticated user from the current session"""

        # Check whether a user is currently authenticated
        user_id = session.get('user_id')

        if user_id:
            # Remove the user ID from the session
            session.pop('user_id', None)

            # Return a successful response without content
            return '', 204

        # Reject logout requests without an active session
        return {'message': 'User not authenticated'}, 401


class RecipeIndex(Resource):
    """Handle retrieval and creation of recipes"""

    def get(self):
        """Return all recipes for authenticated users"""

        # Verify that the request comes from an authenticated user
        user_id = session.get('user_id')

        if not user_id:
            return {'message': 'User not authenticated'}, 401

        # Retrieve all recipes from the database
        recipes = Recipe.query.all()

        # Serialize recipes with their associated user information
        recipe_json = RecipeSchema(many=True).dump(recipes)

        return recipe_json, 200

    def post(self):
        """Create a new recipe associated with the authenticated user"""

        # Verify that the user is authenticated before creating a recipe
        user_id = session.get('user_id')

        if not user_id:
            return {'message': 'User not authenticated'}, 401

        # Retrieve recipe information from the request
        data = request.get_json()
        title = data.get('title')
        instructions = data.get('instructions')
        minutes_to_complete = data.get('minutes_to_complete')

        try:
            # Create a recipe belonging to the authenticated user
            new_recipe = Recipe(
                title=title,
                instructions=instructions,
                minutes_to_complete=minutes_to_complete,
                user_id=user_id
            )

            # Save the new recipe to the database
            db.session.add(new_recipe)
            db.session.commit()

            # Serialize and return the newly created recipe
            recipe_json = RecipeSchema().dump(new_recipe)
            return recipe_json, 201

        except IntegrityError:
            # Roll back database changes when a constraint is violated
            db.session.rollback()
            return {"message": "Unable to create recipe"}, 422

        except ValueError as error:
            # Roll back changes and return the validation error
            db.session.rollback()
            return {"message": str(error)}, 422


# Register API resources and their corresponding URL endpoints
api.add_resource(Signup, '/signup', endpoint='signup')
api.add_resource(CheckSession, '/check_session', endpoint='check_session')
api.add_resource(Login, '/login', endpoint='login')
api.add_resource(Logout, '/logout', endpoint='logout')
api.add_resource(RecipeIndex, '/recipes', endpoint='recipes')


# Start the Flask development server when executed directly
if __name__ == '__main__':
    app.run(port=5555, debug=True)
