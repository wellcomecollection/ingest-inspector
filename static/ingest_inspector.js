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

  if (recentIngests.length > 0) {
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
      listItem.innerHTML += " &ndash; " + ingest["space"] + "/" + ingest["externalIdentifier"];
      ingestList.appendChild(listItem);
    }

    recentIngestsDiv.appendChild(ingestList);
  }
}

const dateFormatter = new Intl.DateTimeFormat(
  [], {"year": "numeric", "month": "long", "day": "numeric", "weekday": "short"}
)

const timeFormatter = new Intl.DateTimeFormat(
  [], {"hour": "numeric", "minute": "numeric", "timeZoneName": "short"}
)

// Localise a date for the current timezone
function localiseDateString(ds) {
  const today = new Date();
  const yesterday = new Date().setDate(new Date().getDate() - 1);

  const date = new Date(Date.parse(ds));

  const isGerman = timeFormatter.resolvedOptions()["locale"] == "de-DE";

  if (dateFormatter.format(date) == dateFormatter.format(today)) {
    if (isGerman) {
      return "heute @ " + timeFormatter.format(date);
    } else {
      return "today @ " + timeFormatter.format(date);
    }
  } else if (dateFormatter.format(date) == dateFormatter.format(yesterday)) {
    if (isGerman) {
      return "gestern @ " + timeFormatter.format(date);
    } else {
      return "yesterday @ " + timeFormatter.format(date);
    }
  } else {
    return dateFormatter.format(date) + " @ " + timeFormatter.format(date);
  }
}

function updateDelta(ds) {
  const today = new Date();
  const date = new Date(Date.parse(ds));

  const delta = today - date;
  const deltaSeconds = Math.floor(delta / 1000);

  const isGerman = timeFormatter.resolvedOptions()["locale"] == "de-DE";

  var result;

  if (isGerman) {
    if (deltaSeconds == 1) {
      result = "vor 1 Sekunde";
    } else if (deltaSeconds < 60) {
      result = "vor " + deltaSeconds + " Sekunde";
    } else if (deltaSeconds < 2 * 60) {
      result = "vor 1 Minute";
    } else if (deltaSeconds < 60 * 60) {
      result = "vor " + Math.floor(deltaSeconds / 60) + " Minuten";
    } else {
      result = ""
    }
  } else {
    if (deltaSeconds < 5) {
      result = "just now";
    } else if (deltaSeconds < 60) {
      result = deltaSeconds + " seconds ago";
    } else if (deltaSeconds < 2 * 60) {
      result = "1 minute ago";
    } else if (deltaSeconds < 60 * 60) {
      result = Math.floor(deltaSeconds / 60) + " minutes ago";
    } else {
      result = ""
    }
  }

  if (result !== "") {
    return " (" + result + ")";
  } else {
    return "";
  }
}
