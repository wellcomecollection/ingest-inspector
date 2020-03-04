function load_ingest() {
  const ingestId = document.getElementById("ingestId").value;
  document.location.href = "/ingests/" + ingestId;
}

function getRecentIngests() {
  const storedIngests = localStorage.getItem("recentIngests");

  if (storedIngests === null) {
    return [];
  }

  return JSON.parse(storedIngests);
}

function storeNewIngest(ingestId, space, externalIdentifier) {
  const recentIngests = getRecentIngests();

  const otherIngests = recentIngests.filter(
    ingest => ingest["ingestId"] != ingestId
  );

  const newIngests = [
    {
      "ingestId": ingestId,
      "space": space,
      "externalIdentifier": externalIdentifier
    }
  ].concat(otherIngests);

  const ingestsToStore = newIngests.slice(0, 10);

  localStorage.setItem("recentIngests", JSON.stringify(ingestsToStore));
}

function renderRecentIngestsList() {
  const recentIngests = getRecentIngests();

  console.log(recentIngests);

  if (recentIngests !== []) {

    recentIngestsDiv = document.getElementById("recentIngests");

    const paragraph = document.createElement("p");
    paragraph.innerHTML = "Recently viewed ingests:";
    recentIngestsDiv.appendChild(paragraph);

    var ingestList = document.createElement("ul");

    for (var i = 0; i < recentIngests.length; i++) {
      var ingest = recentIngests[i];

      var listItem = document.createElement("li");
      var link = document.createElement("a");
      link.href = "/ingests/" + ingest["ingestId"];
      link.innerHTML = ingest["ingestId"];

      listItem.appendChild(link);
      listItem.innerHTML += " &ndash; " + ingest["space"] + " / " + ingest["externalIdentifier"];
      ingestList.appendChild(listItem);
    }

    recentIngestsDiv.appendChild(ingestList);
  }
}
