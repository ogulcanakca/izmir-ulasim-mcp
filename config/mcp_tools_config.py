# API Adresleri
IZTEK_BASE_URL = "https://openapi.izmir.bel.tr/api/iztek"
METRO_BASE_URL = "https://openapi.izmir.bel.tr/api/metro"
TRAMVAY_BASE_URL = "https://openapi.izmir.bel.tr/api/tramvay" 
ACIKVERI_BASE_URL = "https://acikveri.bizizmir.com/tr/api/3/action"

# Kaynak ID'leri
HAT_ARAMA_RESOURCE_ID = "bd6c84f8-49ba-4cf4-81f8-81a0fbb5caa3"
HAT_DETAYLARI_RESOURCE_ID = "81138188-9e50-476d-a1d0-d069e3ec3878"

# CSV Veri Kaynakları
SEFER_SAATLERI_CSV_URL = "https://openfiles.izmir.bel.tr/211488/docs/eshot-otobus-hareketsaatleri.csv"
DURAKLAR_CSV_URL = "https://openfiles.izmir.bel.tr/211488/docs/eshot-otobus-duraklari.csv"
HAT_GUZERGAH_KOORDINATLARI_CSV_URL = "https://openfiles.izmir.bel.tr/211488/docs/eshot-otobus-hat-guzergahlari.csv"
IZBAN_ISTASYONLAR_CSV_URL = "https://acikveri.bizizmir.com/dataset/e3854620-a776-47d4-a63c-9180fc1d4e9e/resource/df6ec7bf-5e75-4f89-9d60-e8da7319517c/download/izban-istasyonlar.csv"
METRO_DURAK_MESAFELERI_CSV_URL = "https://acikveri.bizizmir.com/dataset/b43d973e-8b98-4572-a944-dc39373ab7cb/resource/9a503344-25d5-4f34-8811-65e3108303ca/download/metro-durak-mesafeleri.csv"
TRAMVAY_KARSIYAKA_DURAK_MESAFELERI_CSV_URL = "https://acikveri.bizizmir.com/dataset/b43d973e-8b98-4572-a944-dc39373ab7cb/resource/45d03ae3-f928-441f-bed3-e26c5edd9f42/download/tramvay-karsiyaka-durak-mesafeleri.csv"
TRAMVAY_KONAK_KARA_DURAK_MESAFELERI_CSV_URL = "https://acikveri.bizizmir.com/dataset/b43d973e-8b98-4572-a944-dc39373ab7cb/resource/32930780-fd3a-4b9d-a1b5-a299440a1d6c/download/tramvay-konak-durak-mesafeleri-sag.csv"
TRAMVAY_KONAK_DENIZ_DURAK_MESAFELERI_CSV_URL = "https://acikveri.bizizmir.com/dataset/b43d973e-8b98-4572-a944-dc39373ab7cb/resource/33480acc-873b-43e5-aa3d-2bd6d5fb2134/download/tramvay-konak-durak-mesafeleri-sol.csv"
TRAMVAY_CIGLI_DURAK_MESAFELERI_CSV_URL = "https://acikveri.bizizmir.com/dataset/b43d973e-8b98-4572-a944-dc39373ab7cb/resource/b29426e4-39ae-4b89-8bbd-be6104161fb7/download/tramvay-cigili-durak-mesafeleri.csv"

HTML_TEMPLATE_FOR_LOCATION = """
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

            // Konumu Python'daki Flask sunucusuna gönder ve pencereyi kapat
            fetch('/location', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ latitude: lat, longitude: lon })
            }).then(() => {
                locationDiv.textContent = "Konum alındı, bu pencereyi kapatabilirsiniz.";
            });
        }

        function showError(error) {
            const locationDiv = document.getElementById('location-data');
            let message = "Bilinmeyen bir hata oluştu.";
            switch(error.code) {
                case error.PERMISSION_DENIED:
                    message = "Kullanıcı konum iznini reddetti."
                    break;
                case error.POSITION_UNAVAILABLE:
                    message = "Konum bilgisi mevcut değil."
                    break;
                case error.TIMEOUT:
                    message = "Konum alma isteği zaman aşımına uğradı."
                    break;
            }
            locationDiv.textContent = message;
        }
    </script>
</body>
</html>
"""