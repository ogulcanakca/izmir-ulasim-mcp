# Eshot Ulaşım MCP Sunucusu

İzmir toplu taşıma verilerine erişim sağlayan bir Model Bağlam Protokolü (MCP) sunucusu, AI asistanlarının şehir ulaşım verilerini ve analizlerini sorgulamasına olanak tanır.

## Genel Bakış

Bu MCP sunucusu, İzmir'in [Açık Veri Portalındaki](https://acikveri.bizizmir.com/tr/dataset?organization=eshot) ESHOT veritabanına bağlanır ve anlık otobüs konumlarını, durak bilgilerini, hat güzergahlarını, sefer saatlerini ve yaklaşan araç verilerini almak için çeşitli araçlar sunar. Sunucu, durağa yaklaşan otobüsleri getirme, hat üzerindeki anlık otobüs konumlarını sorgulama, belirli hat ve durak kombinasyonları için yaklaşan araçları filtreleme, durak arama, hat arama ve sefer saatlerini sorgulama gibi işlevler sağlar. Claude Desktop ve Cursor gibi MCP uyumlu AI asistanlarıyla veya agentic yapılarla çalışmak üzere tasarlanmıştır ve [Açık Veri Portalındaki](https://acikveri.bizizmir.com/tr/dataset?organization=eshot) anlık ve canlı ESHOT (şimdilik sadece ESHOT) verileriyle ilgili doğal dil sorguları yapmanızı sağlar.

## Özellikler ve Araçlar

Bu MCP sunucusu, aşağıdaki araçları (tool) içermektedir:

* **`duraga_yaklasan_otobusleri_getir(stop_id)`**: Belirtilen bir durak ID'sine yaklaşmakta olan tüm otobüslerin bilgilerini getirir.
* **`hattin_anlik_otobus_konumlarini_getir(line_id)`**: ID'si girilen bir hatta ait tüm otobüslerin anlık konum bilgilerini getirir.
* **`hattin_duraga_yaklasan_otobuslerini_getir(line_id, stop_id)`**: Belirtilen bir hattın, belirtilen durağa yaklaşmakta olan otobüslerini getirir.
* **`durak_ara(durak_adi)`**: Adında belirtilen metin geçen otobüs duraklarını arar.
* **`hat_ara(hat_bilgisi)`**: Adında veya güzergahında belirtilen metin geçen otobüs hatlarını arar.
* **`hat_sefer_saatlerini_ara(hat_no)`**: Belirtilen hat numarasına göre otobüs sefer saatlerini arar.
* **`hat_guzergah_koordinatlarini_getir(hat_no)`**: Belirtilen hat numarasına ait güzergahın koordinat (enlem/boylam) bilgilerini getirir.
* **`hat_detaylarini_ara(hat_bilgisi)`**: Adında veya güzergahında belirtilen metni içeren hatların çalışma saatleri gibi detaylı bilgilerini arar.

## Kurulum ve Kullanım

### Gereksinimler

* Python 3.11+
* `requests`
* `mcp-cli` 
* `fastmcp` 
* `pandas`

### Kurulum

1.  **Projeyi klonlayın veya indirin:**
    ```bash
    git clone [https://github.com/ogulcanakca/izmir-ulasim-mcp.git](https://github.com/ogulcanakca/izmir-ulasim-mcp.git)
    cd izmir-ulasim-mcp
    ```

2.  **Gerekli kütüphaneleri yükleyin:**
    ```bash
   uv sync
   ```

   pip ile yüklemek isterseniz:

   ```bash
   pip install -r requirements.txt
   ```

### MCP Client Configuration

Sunucuyu Claude Desktop ile kullanmak için:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

Cursor'da kullanmak için:

**macOS**: `$HOME/.cursor/mcp.json`
**Windows**: `%USERPROFILE%\.cursor\mcp.json`

```json
{
  "mcpServers": {
      "izmir_ulasim": {
      "command": "python",
      "args": ["path\\to\\izmir_ulasim_main.py"]
  }
  }
}
```
## Örnek Kullanım

![ornek-sorgular](assets/ornek-sorgular.png)