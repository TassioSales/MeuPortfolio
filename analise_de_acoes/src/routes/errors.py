"""
Error handlers and utility routes.
"""
from flask import Blueprint, render_template, jsonify, current_app
from werkzeug.exceptions import HTTPException
import logging

# Setup logger
error_logger = logging.getLogger('error_routes')

# Create blueprint
errors_bp = Blueprint('errors', __name__)

@errors_bp.app_errorhandler(400)
def bad_request_error(error):
    """Handle 400 Bad Request errors."""
    error_logger.warning(f'Bad Request: {error.description}')
    if request.is_json:
        return jsonify({
            'error': 'Bad Request',
            'message': error.description or 'The request could not be processed.'
        }), 400
    return render_template('errors/400.html', error=error), 400

@errors_bp.app_errorhandler(401)
def unauthorized_error(error):
    """Handle 401 Unauthorized errors."""
    error_logger.warning(f'Unauthorized: {error.description}')
    if request.is_json:
        return jsonify({
            'error': 'Unauthorized',
            'message': error.description or 'Authentication is required to access this resource.'
        }), 401
    return render_template('errors/401.html', error=error), 401

@errors_bp.app_errorhandler(403)
def forbidden_error(error):
    """Handle 403 Forbidden errors."""
    error_logger.warning(f'Forbidden: {error.description}')
    if request.is_json:
        return jsonify({
            'error': 'Forbidden',
            'message': error.description or 'You do not have permission to access this resource.'
        }), 403
    return render_template('errors/403.html', error=error), 403

@errors_bp.app_errorhandler(404)
def not_found_error(error):
    """Handle 404 Not Found errors."""
    error_logger.warning(f'Not Found: {error.description}')
    if request.is_json:
        return jsonify({
            'error': 'Not Found',
            'message': error.description or 'The requested resource was not found.'
        }), 404
    return render_template('errors/404.html', error=error), 404

@errors_bp.app_errorhandler(405)
def method_not_allowed_error(error):
    """Handle 405 Method Not Allowed errors."""
    error_logger.warning(f'Method Not Allowed: {error.description}')
    if request.is_json:
        return jsonify({
            'error': 'Method Not Allowed',
            'message': error.description or 'The method is not allowed for the requested URL.'
        }), 405
    return render_template('errors/405.html', error=error), 405

@errors_bp.app_errorhandler(413)
def request_entity_too_large_error(error):
    """Handle 413 Request Entity Too Large errors."""
    error_logger.warning(f'Request Entity Too Large: {error.description}')
    if request.is_json:
        return jsonify({
            'error': 'Request Entity Too Large',
            'message': error.description or 'The request is larger than the server is willing or able to process.'
        }), 413
    return render_template('errors/413.html', error=error), 413

@errors_bp.app_errorhandler(429)
def too_many_requests_error(error):
    """Handle 429 Too Many Requests errors."""
    error_logger.warning(f'Too Many Requests: {error.description}')
    if request.is_json:
        return jsonify({
            'error': 'Too Many Requests',
            'message': error.description or 'You have exceeded the rate limit for this endpoint.'
        }), 429
    return render_template('errors/429.html', error=error), 429

@errors_bp.app_errorhandler(500)
def internal_server_error(error):
    """Handle 500 Internal Server errors."""
    error_logger.error(f'Internal Server Error: {error.description or str(error)}', exc_info=True)
    if request.is_json:
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An internal server error occurred. Please try again later.'
        }), 500
    return render_template('errors/500.html', error=error), 500

@errors_bp.app_errorhandler(Exception)
def handle_exception(error):
    """Handle all other exceptions."""
    error_logger.error(f'Unhandled Exception: {str(error)}', exc_info=True)
    
    # For HTTP exceptions, use their handlers
    if isinstance(error, HTTPException):
        return error
    
    # For database errors
    if hasattr(error, 'orig') and hasattr(error.orig, 'pgerror'):
        error_logger.error(f'Database Error: {error.orig.pgerror}')
        if request.is_json:
            return jsonify({
                'error': 'Database Error',
                'message': 'A database error occurred. Please try again later.'
            }), 500
    
    # Default error response
    if request.is_json:
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred. Please try again later.'
        }), 500
    
    return render_template('errors/500.html', error=error), 500

@errors_bp.route('/health')
def health_check():
    """Health check endpoint for load balancers and monitoring."""
    try:
        # Check database connection
        db.session.execute('SELECT 1')
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'up'
        }), 200
    except Exception as e:
        error_logger.error(f'Health check failed: {str(e)}')
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'down',
            'error': str(e)
        }), 500

@errors_bp.route('/test/error')
def test_error():
    """Route to test error handling (only in development)."""
    if not current_app.debug:
        return jsonify({'error': 'Not Found'}), 404
    
    # Raise a test exception
    raise Exception('This is a test exception for error handling.')
