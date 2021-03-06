appengine-json-rest
===================
Create a REST-ful JSON api for existing AppEngine db.Model classes.

Sample Implementation:
----------------------
A running AppEngine project that you can test locally is avialable at https://github.com/golsby/appengine-json-rest-sample

Setup Features:
---------------
  * See docs for for create_application() for details.
  * Create your REST URL at any location in your App Engine app.
  * Register models individually
  * Register all models in a module - recursively, if you want
  * Custom authentication/authorization function to restrict access to your API.
  * Require HTTPS (added as a double layer of safety in case you use basic
    authentication - be sure to set up your app.yaml property, too).

Usage:
------
  * Create model:
    * Method: HTTP POST
    * URL: /rest/ModelName
  * Read model:
    * Method: HTTP GET
    * URL: /rest/ModelName/id
  * Update model:
    * Method: HTTP PUT
    * URL: /rest/ModelName/id
  * Delete model:
    * Method: HTTP DELETE
    * URL: /rest/ModelName/id
  * Search for and page through model:
    * Method: HTTP GET
    * URL: /rest/<ModelName>/search
    * Query String Parameters:
      * ref_<property>=<id> - Limit results to <ModelName> instances with ReferenceProperty <property> of ID <id>
      * fgt_<property>=<value> - Limit results to <ModelName> instances with <property> greater than <value>
      * feq_<property>=<value> - Limit results to <ModelName> instances with <property> equal to <value>
      * flt_<property>=<value> - Limit results to <ModelName> instances with <property> less than <value>
      * fle_<property>=<value> - Limit results to <ModelName> instances with <property> less than or equal to <value>
      * fge_<property>=<value> - Limit results to <ModelName> instances with <property> greater than or equal to <value>
      * fne_<property>=<value> - Limit results to <ModelName> instances with <property> not equal to <value>
  * List names of available models:
    * Method: HTTP GET
    * URL: /rest/metadata
  * Query model-specific fields, types, and other data: 
    * Method: HTTP GET
    * URL: /rest/metadata/ModelName

JSON Output Formatting:
-----------------------
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


Currently Supported Types:
--------------------------
**Explicitly Supported Types:**

(Type coersion is performed on reasonable input values)
  * db.DateTimeProperty: ISO 8601 format
  * datetime.datetime: ISO 8601 format
  * db.DateProperty: ISO 8601 format
  * db.TimeProperty: ISO 8601 format
  * db.FloatProperty: float
  * db.GeoPtProperty: {"lat":float,"lon":float}
  * datastore_types.GeoPt: {"lat":float,"lon":float}
  * db.ListProperty
  * db.StringListProperty
  * db.ReferenceProperty:
    Returned as:
        {"module":"package.name", "model": "ModelClassName", "id": 7, "key", "appengine-model-key-string"}
    Converts:
        "appengine-model-key-string"
        or
        {"module":"package.name", "model": "ModelClassName", "id": int}

**Implicitly Supported Types:**

(If you send a type that db.Model likes, it will be stored, otherwise an Exception is raised.
  * datastore_types.Text: unicode
  * db.TextProperty: unicode
  * datastore_types.Category: unicode
  * db.CategoryProperty: unicode
  * datastore_types.Email: unicode
  * db.EmailProperty: unicode
  * datastore_types.Link: unicode
  * db.LinkProperty: unicode
  * datastore_types.PhoneNumber: unicode
  * db.PhoneNumberProperty: unicode
  * datastore_types.PostalAddress: unicode
  * db.PostalAddressProperty: unicode
  * datastore_types.Rating: int
  * db.RatingProperty: int

**NOT Supported Types:**
  * db.Key
  * blobstore.BlobKey
  * blobstore.BlobReferenceProperty
  * users.User
  * datastore_types.Blob
  * db.BlobProperty
  * datastore_types.ByteString
  * db.ByteStringProperty
  * datastore_types.IM
  * db.IMProperty


Thanks:
-------
Several ideas and snippets have been borrowed from other open-source projects.

Special thanks to the developers of:
  * http://code.google.com/p/appengine-rest-server/
  * http://code.google.com/p/gae-json-rest/
