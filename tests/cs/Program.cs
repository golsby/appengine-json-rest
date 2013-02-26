using System.Collections.Generic;
using cs;

namespace csTest
{
  class Program
  {
    static void Main(string[] args)
    {
      var data = new Dictionary<string, object>
                   {
                     {"name", "Pear"}, 
                     {"width", 4}
                   };

      var client = new Client("Fruit", "http://localhost:5000/simple");
      //int id = client.Create(data);

      //var result = client.Get(id);
      //var newData = result.data;
      //newData["width"] = 100;
      //int id2 = client.Update(id, newData);
      //result = client.Get(id2);

      var r = client.All().Filter("name =", "Pear").Order("modified_datetime", true).Fetch(10);
    }
  }
}
