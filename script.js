var map = L.map('map').setView([52.0907, 5.1214], 13); // Utrecht

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

L.marker([52.0907, 5.1214])
  .addTo(map)
  .bindPopup('Hallo Utrecht!')
  .openPopup();