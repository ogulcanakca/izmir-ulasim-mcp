from flask import Flask, render_template_string, request, jsonify
import webbrowser
from threading import Timer

app = Flask(__name__)

# Ayrı bir HTML dosyası yerine, HTML içeriğini doğrudan Python koduna gömüyoruz.
# Bu, tek dosyada çalışmayı kolaylaştırır.
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hassas Konum Alıcı</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background-color: #f0f2f5; flex-direction: column; }
        .container { background-color: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); text-align: center; }
        h1 { color: #333; }
        p { color: #666; margin-bottom: 20px;}
        button { background-color: #007bff; color: white; border: none; padding: 15px 30px; border-radius: 8px; font-size: 16px; cursor: pointer; transition: background-color 0.3s; }
        button:hover { background-color: #0056b3; }
        #location-data { margin-top: 25px; font-size: 18px; color: #1a1a1a; background-color: #e9ecef; padding: 15px; border-radius: 8px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Hassas Konum Bilgisi Al</h1>
        <p>Aşağıdaki düğmeye tıklayarak tarayıcınızdan hassas konum verisi alın.</p>
        <button onclick="getLocation()">Konumumu Al</button>
        <div id="location-data">Konum bilgisi bekleniyor...</div>
    </div>

    <script>
        function getLocation() {
            const locationDiv = document.getElementById('location-data');
            if (navigator.geolocation) {
                locationDiv.textContent = "Konum izni isteniyor...";
                navigator.geolocation.getCurrentPosition(sendPosition, showError);
            } else {
                locationDiv.textContent = "Tarayıcınız konum servisini desteklemiyor.";
            }
        }

        function sendPosition(position) {
            const lat = position.coords.latitude;
            const lon = position.coords.longitude;
            const acc = position.coords.accuracy;

            const locationDiv = document.getElementById('location-data');
            locationDiv.innerHTML = `
                <b>Enlem:</b> ${lat.toFixed(14)}<br>
                <b>Boylam:</b> ${lon.toFixed(14)}<br>
                <b>Doğruluk:</b> ${acc.toFixed(2)} metre
            `;

            // Konumu Python'daki Flask sunucusuna gönder
            fetch('/location', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ latitude: lat, longitude: lon })
            });
        }

        function showError(error) {
            const locationDiv = document.getElementById('location-data');
            switch(error.code) {
                case error.PERMISSION_DENIED:
                    locationDiv.textContent = "Kullanıcı konum iznini reddetti."
                    break;
                case error.POSITION_UNAVAILABLE:
                    locationDiv.textContent = "Konum bilgisi mevcut değil."
                    break;
                case error.TIMEOUT:
                    locationDiv.textContent = "Konum alma isteği zaman aşımına uğradı."
                    break;
                case error.UNKNOWN_ERROR:
                    locationDiv.textContent = "Bilinmeyen bir hata oluştu."
                    break;
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Ana sayfayı oluşturur."""
    return render_template_string(HTML_TEMPLATE)

@app.route('/location', methods=['POST'])
def receive_location():
    """Tarayıcıdan gelen konum verisini alır ve terminale yazdırır."""
    data = request.get_json()
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    
    if latitude and longitude:
        print("\n" + "="*50)
        print("✅ Tarayıcıdan Hassas Konum Alındı!")
        print(f"   Enlem (Latitude):   {latitude}")
        print(f"   Boylam (Longitude): {longitude}")
        print("="*50 + "\n")
        return jsonify({"status": "success"}), 200
    
    return jsonify({"status": "error", "message": "Eksik veri"}), 400

def open_browser():
      webbrowser.open_new("http://127.0.0.1:5000/")

if __name__ == "__main__":
    print("Web sunucusu başlatıldı. Tarayıcınızda açılıyor...")
    print("Hassas konumu almak için açılan web sayfasındaki butona tıklayın.")
    print("Sunucuyu durdurmak için terminalde CTRL+C tuşlarına basın.")
    # Sunucu başladıktan 1 saniye sonra tarayıcıyı aç
    Timer(1, open_browser).start()
    app.run(port=5000, debug=False)