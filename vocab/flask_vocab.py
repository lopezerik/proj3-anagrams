"""
Flask web site with vocabulary matching game
(identify vocabulary words that can be made 
from a scrambled string)
"""

import flask
import logging

# Our own modules
from letterbag import LetterBag
from vocab import Vocab
from jumble import jumbled
import config

###
# Globals
###
app = flask.Flask(__name__)

CONFIG = config.configuration()
app.secret_key = CONFIG.SECRET_KEY  # Should allow using session variables

#
# One shared 'Vocab' object, read-only after initialization,
# shared by all threads and instances.  Otherwise we would have to
# store it in the browser and transmit it on each request/response cycle,
# or else read it from the file on each request/responce cycle,
# neither of which would be suitable for responding keystroke by keystroke.

WORDS = Vocab(CONFIG.VOCAB)

###
# Pages
###


@app.route("/")
@app.route("/index")
def index():
    """The main page of the application"""
    flask.g.vocab = WORDS.as_list()
    flask.session["target_count"] = min(
        len(flask.g.vocab), CONFIG.SUCCESS_AT_COUNT)
    flask.session["jumble"] = jumbled(
        flask.g.vocab, flask.session["target_count"])
    flask.session["matches"] = []
    app.logger.debug("Session variables have been set")
    assert flask.session["matches"] == []
    assert flask.session["target_count"] > 0
    app.logger.debug("At least one seems to be set correctly")
    return flask.render_template('vocab.html')

@app.route("/success")
def success():
    return flask.render_template('success.html')

###############
# AJAX request handlers
#   These return JSON, rather than rendering pages.
###############

prior_value = ""
@app.route("/_clearOnReload")
def clearOnReload():
    global prior_value
    prior_value = ""

@app.route("/_ajaxCheck")
def ajaxCheck():
    '''
    Checks if the user has entered a valid word or not
    '''
    app.logger.debug("Entering ajaxCheck")
    entry = flask.request.args.get("entry", type=str)
    jumble = flask.session["jumble"]
    matches = flask.session.get("matches", [])
    
    # make sure entry is from jumble letters and dictionary
    in_jumble = LetterBag(jumble).contains(entry)
    matched = WORDS.has(entry)
    
    # check if we've tried this before
    global prior_value
    if(entry == prior_value): 
        result = {"valid_word": "False"}
        return flask.jsonify(check=result)
    prior_value = entry
    # response logic
    if matched and in_jumble and not(entry in matches):
        # entry was in dictionary, from jumbled letters, and not a duplicate entry
        matches.append(entry)

        flask.session["mathces"] = matches
        if( len(matches) >= flask.session["target_count"]):
            # reached target
            success_url = flask.url_for("success")
            result = {"valid_word": success_url}
            return flask.jsonify(check=result)
        else:
            result = {"valid_word": "True"}
            return flask.jsonify(check=result)
    else:
        result = {"valid_word": "False"}
        return flask.jsonify(check=result)

################
# Functions used within the templates
#################

@app.template_filter('filt')
def format_filt(something):
    """
    Example of a filter that can be used within
    the Jinja2 code
    """
    return "Not what you asked for"

###################
#   Error handlers
###################


@app.errorhandler(404)
def error_404(e):
    app.logger.warning("++ 404 error: {}".format(e))
    return flask.render_template('404.html'), 404


@app.errorhandler(500)
def error_500(e):
    app.logger.warning("++ 500 error: {}".format(e))
    assert not True  # I want to invoke the debugger
    return flask.render_template('500.html'), 500


@app.errorhandler(403)
def error_403(e):
    app.logger.warning("++ 403 error: {}".format(e))
    return flask.render_template('403.html'), 403


####

if __name__ == "__main__":
    if CONFIG.DEBUG:
        app.debug = True
        app.logger.setLevel(logging.DEBUG)
        app.logger.info(
            "Opening for global access on port {}".format(CONFIG.PORT))
    app.run(port=CONFIG.PORT, host="0.0.0.0")
