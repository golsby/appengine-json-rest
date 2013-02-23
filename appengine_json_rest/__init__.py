"""
Create a REST-ful JSON api for existing AppEngine db.Model classes.

Setup Features:
  * See docs for for create_application() for details.
  * Create your REST URL at any location in your App Engine app.
  * Register models individually
  * Register all models in a module - recursively, if you want
  * Custom authentication/authorization function to restrict access to your API.
  * Require HTTPS (added as a double layer of safety in case you use basic
    authentication - be sure to set up your app.yaml property, too).

Usage:
  * Create model:
     Method: HTTP POST
     URL: /rest/ModelName
  * Read model:
     Method: HTTP GET
     URL: /rest/ModelName/id
  * Update model:
     Method: HTTP PUT
     URL: /rest/ModelName/id
  * Delete model:
     Method: HTTP DELETE
     URL: /rest/ModelName/id
  * Search for and page through model:
     Method: HTTP GET
     URL: /rest/ModelName/search
     QueryString Parameters:
       cursor:

  * List names of available models at /rest/metadata
  * Query model-specific fields, types, and other data: /rest/metadata/ModelName

JSON Output Formatting:
    db.DateProperty, db.DateTimeProperty, and db.TimeProperty classes are
    returned as ISO 8601 format. See http://en.wikipedia.org/wiki/ISO_8601

    Successful API calls return data in the form:
        {
          "status": "success",
          "data": obj
        }

        The value of obj depends on the specific API call that is made.

    Errors are returned in the form:
        {
          "status": "error",
          "message": unicode,
          "type": unicode
        }

        message: extended information about the failure.
        type: the class name of the Exception raised during failure


Several ideas and snippets have been borrowed from other open-source projects.
Special thanks to the developers of:
http://code.google.com/p/appengine-rest-server/
http://code.google.com/p/gae-json-rest/
"""


