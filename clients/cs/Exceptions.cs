using System;
using System.Runtime.Serialization;

namespace cs
{
  [Serializable]
  public class ApiFailureException : Exception
  {
    //
    // For guidelines regarding the creation of new exception types, see
    //    http://msdn.microsoft.com/library/default.asp?url=/library/en-us/cpgenref/html/cpconerrorraisinghandlingguidelines.asp
    // and
    //    http://msdn.microsoft.com/library/default.asp?url=/library/en-us/dncscol/html/csharp07192001.asp
    public string ErrorType { get; set; }

    public ApiFailureException()
    {
    }

    public ApiFailureException(string message, string errorType = null)
      : base(message)
    {
      ErrorType = errorType;
    }

    public ApiFailureException(string message, Exception inner)
      : base(message, inner)
    {
    }

    public ApiFailureException(string message, string errorType, Exception inner)
      : base(message, inner)
    {
      ErrorType = errorType;
    }

    protected ApiFailureException(
      SerializationInfo info,
      StreamingContext context)
      : base(info, context)
    {
    }
  }


  [Serializable]
  public class ObjectMissingException : ApiFailureException
  {
    //
    // For guidelines regarding the creation of new exception types, see
    //    http://msdn.microsoft.com/library/default.asp?url=/library/en-us/cpgenref/html/cpconerrorraisinghandlingguidelines.asp
    // and
    //    http://msdn.microsoft.com/library/default.asp?url=/library/en-us/dncscol/html/csharp07192001.asp
    //

    public ObjectMissingException()
    {
    }

    public ObjectMissingException(string message) : base(message)
    {
    }

    public ObjectMissingException(string message, Exception inner) : base(message, inner)
    {
    }

    protected ObjectMissingException(
      SerializationInfo info,
      StreamingContext context) : base(info, context)
    {
    }
  }

  [Serializable]
  public class AuthenticationRequiredException : ApiFailureException
  {
    //
    // For guidelines regarding the creation of new exception types, see
    //    http://msdn.microsoft.com/library/default.asp?url=/library/en-us/cpgenref/html/cpconerrorraisinghandlingguidelines.asp
    // and
    //    http://msdn.microsoft.com/library/default.asp?url=/library/en-us/dncscol/html/csharp07192001.asp
    //

    public AuthenticationRequiredException()
    {
    }

    public AuthenticationRequiredException(string message) : base(message)
    {
    }

    public AuthenticationRequiredException(string message, Exception inner) : base(message, inner)
    {
    }

    protected AuthenticationRequiredException(
      SerializationInfo info,
      StreamingContext context) : base(info, context)
    {
    }
  }

  [Serializable]
  public class AuthenticationFailedException : ApiFailureException
  {
    //
    // For guidelines regarding the creation of new exception types, see
    //    http://msdn.microsoft.com/library/default.asp?url=/library/en-us/cpgenref/html/cpconerrorraisinghandlingguidelines.asp
    // and
    //    http://msdn.microsoft.com/library/default.asp?url=/library/en-us/dncscol/html/csharp07192001.asp
    //

    public AuthenticationFailedException()
    {
    }

    public AuthenticationFailedException(string message) : base(message)
    {
    }

    public AuthenticationFailedException(string message, Exception inner) : base(message, inner)
    {
    }

    protected AuthenticationFailedException(
      SerializationInfo info,
      StreamingContext context) : base(info, context)
    {
    }
  }

  [Serializable]
  public class ModelNotRegisteredException : ApiFailureException
  {
    //
    // For guidelines regarding the creation of new exception types, see
    //    http://msdn.microsoft.com/library/default.asp?url=/library/en-us/cpgenref/html/cpconerrorraisinghandlingguidelines.asp
    // and
    //    http://msdn.microsoft.com/library/default.asp?url=/library/en-us/dncscol/html/csharp07192001.asp
    //

    public ModelNotRegisteredException()
    {
    }

    public ModelNotRegisteredException(string message) : base(message)
    {
    }

    public ModelNotRegisteredException(string message, Exception inner) : base(message, inner)
    {
    }

    protected ModelNotRegisteredException(
      SerializationInfo info,
      StreamingContext context) : base(info, context)
    {
    }
  }

  [Serializable]
  public class HttpsRequiredException : ApiFailureException
  {
    //
    // For guidelines regarding the creation of new exception types, see
    //    http://msdn.microsoft.com/library/default.asp?url=/library/en-us/cpgenref/html/cpconerrorraisinghandlingguidelines.asp
    // and
    //    http://msdn.microsoft.com/library/default.asp?url=/library/en-us/dncscol/html/csharp07192001.asp
    //

    public HttpsRequiredException()
    {
    }

    public HttpsRequiredException(string message) : base(message)
    {
    }

    public HttpsRequiredException(string message, Exception inner) : base(message, inner)
    {
    }

    protected HttpsRequiredException(
      SerializationInfo info,
      StreamingContext context) : base(info, context)
    {
    }
  }

  [Serializable]
  public class OperatorNotFoundException : ApiFailureException
  {
    //
    // For guidelines regarding the creation of new exception types, see
    //    http://msdn.microsoft.com/library/default.asp?url=/library/en-us/cpgenref/html/cpconerrorraisinghandlingguidelines.asp
    // and
    //    http://msdn.microsoft.com/library/default.asp?url=/library/en-us/dncscol/html/csharp07192001.asp
    //

    public OperatorNotFoundException()
    {
    }

    public OperatorNotFoundException(string message) : base(message)
    {
    }

    public OperatorNotFoundException(string message, Exception inner) : base(message, inner)
    {
    }

    protected OperatorNotFoundException(
      SerializationInfo info,
      StreamingContext context) : base(info, context)
    {
    }
  }
}
