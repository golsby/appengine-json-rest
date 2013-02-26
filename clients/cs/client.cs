using System;
using System.Collections.Generic;
using System.Net;
using System.Text;
using Newtonsoft.Json;

namespace cs
{
  public class ListResult
  {
    public string status = null;
    public ModelList data;
    public string message;
    public string type;
  }

  public class SingleResult
  {
    public string status = null;
    public Model data;
    public string message;
    public string type;
  }

  public class IntegerResult
  {
    public string status;
    public int data;
    public string message;
    public string type;
  }

  public class ModelList
  {
    public List<Model> models;
    public string cursor;
  }

  public class Model : Dictionary<string, object>
  {
  }

  public class Query
  {
    readonly Client m_client;
    readonly Dictionary<string, string> m_filter_methods = new Dictionary<string,string>
                                                             {
                                                                {"=", "feq_"},
                                                                {">", "fgt_"},
                                                                {">=", "fge_"},
                                                                {"<", "flt_"},
                                                                {"<=", "fle_"},
                                                                {"!=", "fne_"}
                                                             };

    readonly List<KeyValuePair<string, object>> m_params = new List<KeyValuePair<string,object>>();
    public Query(Client client)
    {
      m_client = client;
    }

    public Query Filter(string expression, object value)
    {
      if (!expression.Contains(" "))
        throw new OperatorNotFoundException(
          string.Format(
            "Operator not found in expression '{0}'. (Are you missing a space between the property name and the operator?)",
            expression));

      var list = expression.Split(" ".ToCharArray(), 2);
      string property = list[0];
      string operator_ = list[1];
      string prefix;
      if (m_filter_methods.TryGetValue(operator_, out prefix))
      {
        AddParameter(string.Format("{0}{1}", prefix, property), value);
        return this;
      }

      throw new OperatorNotFoundException("Unsupported operator: " + operator_);
    }

    public Query Order(string property, bool descending = false)
    {
      if (descending)
        AddParameter("order", string.Format("-{0}", property));
      else
        AddParameter("order", property);
      return this;
    }

    public Query WithCursor(string cursor)
    {
      AddParameter("cursor", cursor);
      return this;
    }

    public ModelList Fetch(int limit = 0)
    {
      if (limit > 0)
        AddParameter("limit", limit);

      var c = new WebClient();
      var querystring = new StringBuilder();
      foreach (var p in m_params)
      {
        if (querystring.Length > 0)
          querystring.Append("&");
        querystring.Append(Uri.EscapeDataString(p.Key));
        querystring.Append("=");
        querystring.Append(Uri.EscapeDataString(string.Format("{0}", p.Value)));
      }

      string url = m_client.ApiUrl("search");
      if (querystring.Length > 0)
        url += "?" + querystring;

      string json = c.DownloadString(url);
      var response = JsonConvert.DeserializeObject<ListResult>(json);
      if (response.status == "success")
        return response.data;

      throw new ApiFailureException(response.message, response.type);
    }

    private void AddParameter(string name, object value)
    {
      m_params.Add(new KeyValuePair<string, object>(name, value));
    }
  }

  public class Client
  {
    readonly string m_model_name = null;
    readonly string m_api_path = null;
    public Client(string modelName, string apiPath)
    {
      m_model_name = modelName;
      m_api_path = apiPath.TrimEnd("/".ToCharArray());
    }

    public string ApiUrl(object id=null)
    {
      var result = new StringBuilder();
      result.Append(m_api_path).Append("/").Append(m_model_name);
      if (id != null)
        result.Append("/").Append(id.ToString());

      return result.ToString();
    }

    public int Create(Dictionary<string, object> data)
    {
      var webClient = new WebClient();
      webClient.Headers["Content-Type"] = "application/json; charset=utf-8";
      string url = ApiUrl();
      string jsonRequest = JsonConvert.SerializeObject(data);
      string jsonResponse = webClient.UploadString(url, "POST", jsonRequest);
      var response = JsonConvert.DeserializeObject<IntegerResult>(jsonResponse);
      if (response.status == "success")
        return response.data;

      throw new ApiFailureException(response.message, response.type);
    }

    public Model Get(int id)
    {
      var webClient = new WebClient();
      string url = ApiUrl(id);
      string json = webClient.DownloadString(url);
      var response = JsonConvert.DeserializeObject<SingleResult>(json);
      if (response.status == "success")
        return response.data;

      throw new ApiFailureException(response.message, response.type);
    }

    public int Update(int id, Dictionary<string, object> data)
    {
      var webClient = new WebClient();
      webClient.Headers["Content-Type"] = "application/json; charset=utf-8";
      string url = ApiUrl(id);
      string jsonRequest = JsonConvert.SerializeObject(data);
      string jsonResponse = webClient.UploadString(url, "PUT", jsonRequest);
      var response = JsonConvert.DeserializeObject<IntegerResult>(jsonResponse);
      if (response.status == "success")
        return response.data;

      throw new ApiFailureException(response.message, response.type);
    }

    public int Delete(int id)
    {
      var webClient = new WebClient();
      webClient.Headers["Content-Type"] = "application/json; charset=utf-8";
      string url = ApiUrl(id);
      string jsonResponse = webClient.UploadString(url, "DELETE");
      var response = JsonConvert.DeserializeObject<IntegerResult>(jsonResponse);
      if (response.status == "success")
        return response.data;

      throw new ApiFailureException(response.message, response.type);
    }

    public Query All()
    {
      return new Query(this);
    }
  }
}
