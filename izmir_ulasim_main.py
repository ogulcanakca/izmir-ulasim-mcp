import logging
import requests
import json
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
import os
from thefuzz import process 
import pyarrow 
import urllib.request
import ssl

from mcp.server.fastmcp import FastMCP

from config.mcp_tools_config import (
    IZTEK_BASE_URL,
    ACIKVERI_BASE_URL,
    DURAK_ARAMA_RESOURCE_ID,
    HAT_ARAMA_RESOURCE_ID,
    HAT_GUZERGAH_KOORDINATLARI_RESOURCE_ID,
    HAT_DETAYLARI_RESOURCE_ID,
    SEFER_SAATLERI_CSV_URL
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("izmir_ulasim")

def load_or_process_stops_data(
    raw_csv_filename='eshot-otobus-duraklari.csv',
    processed_parquet_filename='processed_stops.parquet'
) -> (Optional[pd.DataFrame], List[str]):
    """
    İşlenmiş Parquet dosyası varsa doğrudan onu yükler. Yoksa, ham CSV'yi işler,
    Parquet olarak kaydeder ve sonucu döndürür. Dosya yollarını betiğin konumuna göre ayarlar.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    raw_csv_path = os.path.join(script_dir, 'files', raw_csv_filename)
    processed_parquet_path = os.path.join(script_dir, 'files', processed_parquet_filename)

    if os.path.exists(processed_parquet_path):
        try:
            logger.info(f"Hızlı başlangıç: İşlenmiş veri '{processed_parquet_path}' yükleniyor...")
            df = pd.read_parquet(processed_parquet_path)
            unique_names = df['DURAK_ADI'].dropna().unique().tolist()
            logger.info(f"İşlenmiş durak verileri {len(unique_names)} kayıt ile başarıyla yüklendi.")
            return df, unique_names
        except Exception as e:
            logger.error(f"İşlenmiş Parquet dosyası ('{processed_parquet_path}') okunurken hata oluştu: {e}. Ham veri yeniden işlenecek.")

    try:
        logger.info(f"İlk çalıştırma: Ham veri '{raw_csv_path}' işleniyor...")
        
        df = pd.read_csv(raw_csv_path, delimiter=';') 

        df['ENLEM'] = df['ENLEM'].astype(str).str.replace('.', '', regex=False).str.replace(',', '.')
        df['BOYLAM'] = df['BOYLAM'].astype(str).str.replace('.', '', regex=False).str.replace(',', '.')
        df['ENLEM'] = pd.to_numeric(df['ENLEM'], errors='coerce')
        df['BOYLAM'] = pd.to_numeric(df['BOYLAM'], errors='coerce')

        df.to_parquet(processed_parquet_path)
        logger.info(f"Temizlenmiş veri '{processed_parquet_path}' olarak başarıyla kaydedildi.")

        unique_names = df['DURAK_ADI'].dropna().unique().tolist()
        return df, unique_names
        
    except FileNotFoundError:
        logger.error(f"HATA: Ham veri dosyası '{raw_csv_path}' konumunda bulunamadı! Lütfen dosyanın doğru yerde olduğundan emin olun.")
        return None, []
    except Exception as e:
        logger.error(f"Ham durak dosyası ('{raw_csv_path}') işlenirken genel bir hata oluştu: {e}")
        return None, []

stops_df, UNIQUE_STOP_NAMES = load_or_process_stops_data()

# --- Tool 1: Durağa Yaklaşan Tüm Otobüsler ---
@mcp.tool()
def duraga_yaklasan_otobusleri_getir(stop_id: int) -> Optional[List[Dict[str, Any]]]:
    """
    Belirtilen bir durak ID'sine yaklaşmakta olan tüm otobüslerin
    bilgilerini getirir.
    
    Args:
        stop_id (int): Bilgisi alınacak durağın ID'si.
        
    Returns:
        Otobüs bilgilerini içeren bir liste veya hata durumunda None.
    """
    url = f"{IZTEK_BASE_URL}/duragayaklasanotobusler/{stop_id}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 204:
            return [] 
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f"API isteği sırasında hata (duraga_yaklasan_otobusler): {e}")
        return None
    return None

# --- Tool 2: Belirli Bir Hattın Anlık Otobüs Konumları ---
@mcp.tool()
def hattin_anlik_otobus_konumlarini_getir(line_id: int) -> Optional[List[Dict[str, Any]]]:
    """
    ID'si girilen bir hatta ait tüm otobüslerin anlık konum bilgilerini getirir.

    Args:
        line_id (int): Hat numarası (ID'si).

    Returns:
        Otobüs konum bilgilerini içeren bir liste veya hata durumunda None.
    """
    url = f"{IZTEK_BASE_URL}/hatotobuskonumlari/{line_id}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data.get("HataMesaj"):
                logger.error(f"API Hatası (hatotobuskonumlari): {data['HataMesaj']}")
                return None
            return data.get("HatOtobusKonumlari", [])
        elif response.status_code == 204:
            return []
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f"API isteği sırasında hata (hatotobuskonumlari): {e}")
        return None
    return None

# --- Tool 3: Hattın Durağa Yaklaşan Otobüsleri ---
@mcp.tool()
def hattin_duraga_yaklasan_otobuslerini_getir(line_id: int, stop_id: int) -> Optional[List[Dict[str, Any]]]:
    """
    Belirtilen bir hattın, belirtilen durağa yaklaşmakta olan otobüslerini getirir.

    Args:
        line_id (int): Hat numarası (ID'si).
        stop_id (int): Durak numarası (ID'si).

    Returns:
        Otobüs bilgilerini içeren bir liste veya hata durumunda None.
    """
    url = f"{IZTEK_BASE_URL}/hattinyaklasanotobusleri/{line_id}/{stop_id}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 204:
            return []
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f"API isteği sırasında hata (hattinyaklasanotobusleri): {e}")
        return None
    return None

# --- ACIKVERI API için Genel Arama Fonksiyonu ---
def _search_acikveri(
    resource_id: str,
    query: Optional[str] = None,
    filters: Optional[Dict[str, Any]] = None,
    limit: int = 10
) -> Optional[List[Dict[str, Any]]]:
    """
    acikveri.bizizmir.com için genel datastore_search sorgusu yapar.
    `query` (tam metin arama) veya `filters` (alan bazlı filtre) kullanılabilir.
    """
    url = f"{ACIKVERI_BASE_URL}/datastore_search"
    params: Dict[str, Any] = {'resource_id': resource_id, 'limit': limit}
    if query:
        params['q'] = query
    if filters:
        params['filters'] = json.dumps(filters)

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        if data.get('success'):
            return data.get('result', {}).get('records', [])
        else:
            logger.error(f"ACIKVERI API hatası: {data.get('error')}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"ACIKVERI API isteği sırasında hata: {e}")
        return None
    return None


# --- Tool 4: Akıllı Durak Arama ---
@mcp.tool()
def durak_ara(durak_adi: str, limit: int = 5, benzerlik_esigi: int = 80) -> Optional[List[Dict[str, Any]]]:
    """
    Adında belirtilen metin geçen otobüs duraklarını arar.
    Yazım hatalarını tolere eder ve yerel durak listesinden en benzer sonuçları bulur.

    Args:
        durak_adi (str): Aranacak durak adı veya bir kısmı.
        limit (int): Döndürülecek maksimum sonuç sayısı.
        benzerlik_esigi (int): Bir sonucun eşleşme olarak kabul edilmesi için gereken minimum benzerlik skoru (0-100).

    Returns:
        Durak bilgilerini içeren kayıtların listesi.
    """
    if stops_df is None or not UNIQUE_STOP_NAMES:
        logger.error("Durak verileri yüklenemediği için durak araması yapılamıyor.")
        return [{"hata": "Durak veritabanı hazır değil."}]
    
    matches = process.extract(durak_adi, UNIQUE_STOP_NAMES, limit=limit*2)
    
    good_matches = [match[0] for match in matches if match[1] >= benzerlik_esigi]
    
    if not good_matches:
        return []

    results_df = stops_df[stops_df['DURAK_ADI'].isin(good_matches)].head(limit)
    
    return results_df.to_dict('records')


# --- Tool 5: Otobüs Hattı Arama ---
@mcp.tool()
def hat_ara(hat_bilgisi: str, limit: int = 5) -> Optional[List[Dict[str, Any]]]:
    """
    Adında veya güzergahında belirtilen metin geçen otobüs hatlarını arar.

    Args:
        hat_bilgisi (str): Aranacak hat adı, numarası veya güzergah bilgisi.
        limit (int): Döndürülecek maksimum sonuç sayısı.

    Returns:
        Hat bilgilerini içeren kayıtların listesi.
    """
    return _search_acikveri(
        resource_id=HAT_ARAMA_RESOURCE_ID,
        query=hat_bilgisi,
        limit=limit
    )

# --- Tool 6: Hat Sefer Saati Arama ---
def _indir_ve_cache_le_sefer_saatleri_csv() -> Optional[str]:
    """
    Sefer saatleri CSV dosyasını indirir ve yerel bir kopyasını oluşturur.
    Dosya zaten varsa tekrar indirmez.
    """
    klasor = "data"
    dosya_yolu = os.path.join(klasor, "eshot-otobus-hareketsaatleri.csv")

    try:
        if not os.path.exists(dosya_yolu):
            logger.info(f"'{dosya_yolu}' bulunamadı, indiriliyor...")
            if not os.path.exists(klasor):
                os.makedirs(klasor)
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            with urllib.request.urlopen(SEFER_SAATLERI_CSV_URL, context=ssl_context) as response, \
                 open(dosya_yolu, 'wb') as out_file:
                out_file.write(response.read())
            logger.info("CSV dosyası başarıyla indirildi.")
        return dosya_yolu
    except Exception as e:
        logger.error(f"CSV indirilirken veya işlenirken hata oluştu: {e}")
        return None

@mcp.tool()
def hat_sefer_saatlerini_ara(hat_no: int, limit: int = 50) -> Optional[List[Dict[str, Any]]]:
    """
    Belirtilen hat numarasına göre otobüs sefer saatlerini CSV dosyasından arar.

    Args:
        hat_no (int): Sefer saatleri aranacak hat numarası.
        limit (int): Döndürülecek maksimum sonuç sayısı.

    Returns:
        Sefer saati bilgilerini içeren kayıtların listesi.
    """
    dosya_yolu = _indir_ve_cache_le_sefer_saatleri_csv()
    if not dosya_yolu:
        return None

    try:
        df = pd.read_csv(dosya_yolu, sep=';')
        hat_verileri = df[df['HAT_NO'] == hat_no].head(limit)

        if hat_verileri.empty:
            return []

        return hat_verileri.to_dict('records')
    except Exception as e:
        logger.error(f"Sefer saatleri CSV dosyası okunurken hata oluştu: {e}")
        return None

# --- Tool 7: Hat Güzergah Koordinatlarını Getir ---
@mcp.tool()
def hat_guzergah_koordinatlarini_getir(hat_no: int, limit: int = 250) -> Optional[List[Dict[str, Any]]]:
    """
    Belirtilen hat numarasına ait güzergahın koordinat (enlem/boylam)
    bilgilerini getirir.

    Args:
        hat_no (int): Güzergahı alınacak hat numarası.
        limit (int): Döndürülelecek maksimum koordinat noktası sayısı.

    Returns:
        Güzergah koordinatlarını içeren kayıtların listesi.
    """
    filters = {'HAT_NO': str(hat_no)}
    return _search_acikveri(
        resource_id=HAT_GUZERGAH_KOORDINATLARI_RESOURCE_ID,
        filters=filters,
        limit=limit
    )

# --- Tool 8: Hat Detaylarını Ara ---
@mcp.tool()
def hat_detaylarini_ara(hat_bilgisi: str, limit: int = 5) -> Optional[List[Dict[str, Any]]]:
    """
    Adında veya güzergahında belirtilen metni içeren hatların
    çalışma saatleri gibi detaylı bilgilerini arar.

    Args:
        hat_bilgisi (str): Aranacak hat adı veya güzergah bilgisi.
        limit (int): Döndürülecek maksimum sonuç sayısı.

    Returns:
        Hat detaylarını içeren kayıtların listesi.
    """
    return _search_acikveri(
        resource_id=HAT_DETAYLARI_RESOURCE_ID,
        query=hat_bilgisi,
        limit=limit
    )

if __name__ == "__main__":
    mcp.run(transport="stdio")