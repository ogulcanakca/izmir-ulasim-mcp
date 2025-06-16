import logging
import requests
import json
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
import os
import urllib.request
import ssl
import numpy as np
from flask import Flask, render_template_string, request, jsonify
import webbrowser
from threading import Timer, Event, Thread
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, time
from zoneinfo import ZoneInfo


from mcp.server.fastmcp import FastMCP

from config.mcp_tools_config import (
    IZTEK_BASE_URL,
    ACIKVERI_BASE_URL,
    HAT_ARAMA_RESOURCE_ID,
    HAT_DETAYLARI_RESOURCE_ID,
    SEFER_SAATLERI_CSV_URL,
    DURAKLAR_CSV_URL,
    HAT_GUZERGAH_KOORDINATLARI_CSV_URL,
    IZBAN_ISTASYONLAR_CSV_URL,
    HTML_TEMPLATE_FOR_LOCATION
)

logging.basicConfig(
    level=logging.INFO,
    filename='mcp.log',
    filemode='w',
    force=True,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

mcp = FastMCP("izmir_ulasim")

def _download_csv(url: str, file_path: str) -> bool:
    """
    Verilen URL'den bir CSV dosyasını indirir ve belirtilen yola kaydeder.
    Mevcut dosyanın üzerine yazar. SSL doğrulaması atlanır.
    """
    logger.info(f"'{os.path.basename(file_path)}' için '{url}' adresinden güncel veri indiriliyor...")
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        with urllib.request.urlopen(url, context=ssl_context) as response, \
             open(file_path, 'wb') as out_file:
            out_file.write(response.read())
        logger.info(f"'{os.path.basename(file_path)}' başarıyla indirildi ve güncellendi.")
        return True
    except Exception as e:
        logger.error(f"'{os.path.basename(file_path)}' indirilirken hata oluştu: {e}")
        return False

def load_or_process_stops_data(
    raw_csv_filename='eshot-otobus-duraklari.csv',
    processed_parquet_filename='processed_stops.parquet'
) -> Optional[pd.DataFrame]:
    """
    Durak verilerini her zaman güncel CSV'den indirir, işler,
    Parquet olarak kaydeder ve sonucu döndürür.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    raw_csv_path = os.path.join(script_dir, 'data', raw_csv_filename)
    processed_parquet_path = os.path.join(script_dir, 'data', processed_parquet_filename)

    if not _download_csv(DURAKLAR_CSV_URL, raw_csv_path):
        logger.error(f"Durak CSV dosyası indirilemediği için durak verisi yüklenemedi.")
        return None

    try:
        logger.info(f"İndirilen ham durak verisi '{raw_csv_path}' işleniyor...")
        
        df = pd.read_csv(raw_csv_path, delimiter=';', decimal=',') 

        df['ENLEM'] = pd.to_numeric(df['ENLEM'], errors='coerce')
        df['BOYLAM'] = pd.to_numeric(df['BOYLAM'], errors='coerce')

        df = df.dropna(subset=['ENLEM', 'BOYLAM'])

        df.to_parquet(processed_parquet_path, index=False)
        logger.info(f"Temizlenmiş durak verisi '{processed_parquet_path}' olarak başarıyla kaydedildi.")

        return df
        
    except FileNotFoundError:
        logger.error(f"HATA: Ham veri dosyası '{raw_csv_path}' konumunda bulunamadı!")
        return None
    except Exception as e:
        logger.error(f"Ham durak dosyası ('{raw_csv_path}') işlenirken genel bir hata oluştu: {e}")
        return None

def load_or_process_route_coords_data(
    raw_csv_filename='eshot-otobus-hat-guzergahlari.csv',
    processed_parquet_filename='processed_route_coords.parquet'
) -> Optional[pd.DataFrame]:
    """
    Güzergah koordinat verilerini her zaman güncel CSV'den indirir, işler,
    Parquet olarak kaydeder ve sonucu döndürür.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    raw_csv_path = os.path.join(script_dir, 'data', raw_csv_filename)
    processed_parquet_path = os.path.join(script_dir, 'data', processed_parquet_filename)

    if not _download_csv(HAT_GUZERGAH_KOORDINATLARI_CSV_URL, raw_csv_path):
        logger.error(f"Güzergah koordinatları CSV dosyası indirilemediği için veri yüklenemedi.")
        return None

    try:
        logger.info(f"İndirilen ham güzergah koordinat verisi '{raw_csv_path}' işleniyor...")
        
        df = pd.read_csv(raw_csv_path, delimiter=';', decimal=',') 
        logger.info(f"CSV başarıyla okundu. '{os.path.basename(raw_csv_path)}' dosyasındaki sütunlar: {df.columns.tolist()}")
        logger.info(f"CSV'den okunan ilk 5 satır:\n{df.head().to_string()}")

        required_cols = ['HAT_NO', 'ENLEM', 'BOYLAM']
        if not all(col in df.columns for col in required_cols):
            logger.error(f"HATA: Güzergah CSV dosyasında beklenen sütunlar bulunamadı.")
            logger.error(f"Beklenen Sütunlar: {required_cols}")
            logger.error(f"Dosyadaki Sütunlar: {df.columns.tolist()}")
            return None

        df['SIRA'] = df.index

        df['ENLEM'] = pd.to_numeric(df['ENLEM'], errors='coerce')
        df['BOYLAM'] = pd.to_numeric(df['BOYLAM'], errors='coerce')
        df['HAT_NO'] = pd.to_numeric(df['HAT_NO'], errors='coerce')

        df = df.dropna(subset=['HAT_NO', 'ENLEM', 'BOYLAM'])
        df['HAT_NO'] = df['HAT_NO'].astype(int)
        df['SIRA'] = df['SIRA'].astype(int)

        df.to_parquet(processed_parquet_path, index=False)
        logger.info(f"Temizlenmiş güzergah koordinat verisi '{processed_parquet_path}' olarak başarıyla kaydedildi.")

        return df
        
    except FileNotFoundError:
        logger.error(f"HATA: Ham veri dosyası '{raw_csv_path}' konumunda bulunamadı!")
        return None
    except Exception as e:
        logger.error(f"Ham güzergah koordinat dosyası ('{raw_csv_path}') işlenirken genel bir hata oluştu: {e}", exc_info=True)
        return None

def load_or_process_izban_stations_data(
    raw_csv_filename='izban-istasyonlar.csv',
    processed_parquet_filename='processed_izban_stations.parquet'
) -> Optional[pd.DataFrame]:
    """
    İZBAN istasyon verilerini her zaman güncel CSV'den indirir, işler,
    Parquet olarak kaydeder ve sonucu döndürür.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    raw_csv_path = os.path.join(script_dir, 'data', raw_csv_filename)
    processed_parquet_path = os.path.join(script_dir, 'data', processed_parquet_filename)

    if not _download_csv(IZBAN_ISTASYONLAR_CSV_URL, raw_csv_path):
        logger.error(f"İZBAN istasyon CSV dosyası indirilemediği için veri yüklenemedi.")
        return None

    try:
        logger.info(f"İndirilen ham İZBAN istasyon verisi '{raw_csv_path}' işleniyor...")
        
        df = pd.read_csv(raw_csv_path, delimiter=';') 

        df['ENLEM'] = pd.to_numeric(df['ENLEM'], errors='coerce')
        df['BOYLAM'] = pd.to_numeric(df['BOYLAM'], errors='coerce')

        df = df.dropna(subset=['ENLEM', 'BOYLAM'])

        df.to_parquet(processed_parquet_path, index=False)
        logger.info(f"Temizlenmiş İZBAN istasyon verisi '{processed_parquet_path}' olarak başarıyla kaydedildi.")

        return df
        
    except FileNotFoundError:
        logger.error(f"HATA: Ham veri dosyası '{raw_csv_path}' konumunda bulunamadı!")
        return None
    except Exception as e:
        logger.error(f"Ham İZBAN istasyon dosyası ('{raw_csv_path}') işlenirken genel bir hata oluştu: {e}")
        return None

stops_df = load_or_process_stops_data()
route_coords_df = load_or_process_route_coords_data()
izban_stations_df = load_or_process_izban_stations_data()

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
    Hata durumunda açıklayıcı bir JSON mesajı döner.
    """
    url = f"{IZTEK_BASE_URL}/hattinyaklasanotobusleri/{line_id}/{stop_id}"
    try:
        response = requests.get(url)
        
        if response.status_code == 200:
            return response.json()
        if response.status_code == 204:
            return [] 

        elif response.status_code == 404:
            logger.error(f"API Hatası (404): Hat ID '{line_id}' veya Durak ID '{stop_id}' bulunamadı.")
            return {
                "hata": "GEÇERSİZ_ID",
                "mesaj": f"API'de '{line_id}' numaralı hat veya '{stop_id}' numaralı durak bulunamadı. Lütfen ID'leri kontrol edin."
            }
        else:
            logger.error(f"API Hatası ({response.status_code}): Beklenmedik durum.")
            return {
                "hata": "API_YANIT_HATASI",
                "mesaj": f"API'den beklenmedik bir durum kodu ({response.status_code}) alındı."
            }
            
    except requests.exceptions.RequestException as e:
        logger.error(f"API isteği sırasında hata (hattinyaklasanotobusleri): {e}")
        return {
            "hata": "AĞ_HATASI",
            "mesaj": f"API'ye bağlanırken bir ağ hatası oluştu: {e}"
        }

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
def durak_ara(durak_adi: str, limit: int = 5) -> Optional[List[Dict[str, Any]]]:
    """
    Adında belirtilen metin geçen otobüs duraklarını arar.

    Args:
        durak_adi (str): Aranacak durak adı veya bir kısmı.
        limit (int): Döndürülecek maksimum sonuç sayısı.

    Returns:
        Durak bilgilerini içeren kayıtların listesi.
    """
    if stops_df is None:
        logger.error("Durak verileri yüklenemediği için durak araması yapılamıyor.")
        return [{"hata": "Durak veritabanı hazır değil."}]

    results_df = stops_df[stops_df['DURAK_ADI'].str.contains(durak_adi, case=False, na=False)].head(limit)

    return results_df.to_dict('records')


# --- Tool 5: İZBAN İstasyon Arama ---
@mcp.tool()
def izban_istasyon_ara(istasyon_adi: str, limit: int = 5) -> Optional[List[Dict[str, Any]]]:
    """
    Adında belirtilen metin geçen İZBAN istasyonlarını arar.

    Args:
        istasyon_adi (str): Aranacak istasyon adı veya bir kısmı.
        limit (int): Döndürülecek maksimum sonuç sayısı.

    Returns:
        İstasyon bilgilerini içeren kayıtların listesi.
    """
    if izban_stations_df is None:
        logger.error("İZBAN istasyon verileri yüklenemediği için istasyon araması yapılamıyor.")
        return [{"hata": "İZBAN istasyon veritabanı hazır değil."}]

    results_df = izban_stations_df[izban_stations_df['ISTASYON_ADI'].str.contains(istasyon_adi, case=False, na=False)].head(limit)

    return results_df.to_dict('records')


# --- Tool 6: İZBAN Sefer Saatlerini Getir ---
@mcp.tool()
def izban_sefer_saatlerini_getir(kalkis_istasyon_id: int, varis_istasyon_id: int) -> Optional[List[Dict[str, Any]]]:
    """
    Belirtilen iki İZBAN istasyonu arasındaki sefer saatlerini getirir.
    İstasyon ID'lerini bulmak için `izban_istasyon_ara` aracı kullanılabilir.

    Args:
        kalkis_istasyon_id (int): Kalkış istasyonunun ID'si.
        varis_istasyon_id (int): Varış istasyonunun ID'si.

    Returns:
        Sefer saati bilgilerini içeren bir liste veya hata durumunda None.
    """
    url = f"https://openapi.izmir.bel.tr/api/izban/sefersaatleri/{kalkis_istasyon_id}/{varis_istasyon_id}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 204:
            logger.info(f"'{kalkis_istasyon_id}' ve '{varis_istasyon_id}' arasında sefer bulunamadı.")
            return [] 
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f"İZBAN sefer saatleri API isteği sırasında hata: {e}")
        return None
    return None


# --- Tool 7: İZBAN Tutar Hesaplama ---
@mcp.tool()
def izban_tutar_hesapla(binis_istasyon_id: int, inis_istasyon_id: int, aktarma_sayisi: int) -> Optional[Dict[str, Any]]:
    """
    'Gittiğin Kadar Öde' sistemine göre İZBAN yolculuk ücretini hesaplar.
    Halk Taşıt saat dilimlerini (her gün 05:00-07:00 ve 19:00-20:00) otomatik olarak kontrol eder.

    Args:
        binis_istasyon_id (int): Biniş yapılacak istasyonun ID'si.
        inis_istasyon_id (int): İniş yapılacak istasyonun ID'si.
        aktarma_sayisi (int): Yapılan aktarma sayısı (0, 1, 2 veya 3).

    Returns:
        Ücret detaylarını ve Halk Taşıt saati uygulanıp uygulanmadığı bilgisini içeren bir sözlük veya hata durumunda None.
    """
    try:
        tz = ZoneInfo("Europe/Istanbul")
        now = datetime.now(tz).time()

        morning_start = time(5, 0)
        morning_end = time(7, 0)
        evening_start = time(19, 0)
        evening_end = time(20, 0)

        is_halk_tasit_saati = (morning_start <= now < morning_end) or \
                              (evening_start <= now < evening_end)
        logger.info(f"Halk Taşıt saati kontrolü: Şu anki saat ({now}) için durum: {is_halk_tasit_saati}")
    except Exception as e:
        logger.warning(f"Saat dilimi bilgisi alınamadı, 'halk_tasit_saati_mi' false varsayılıyor. Hata: {e}")
        is_halk_tasit_saati = False

    url = f"https://openapi.izmir.bel.tr/api/izban/tutarhesaplama/{binis_istasyon_id}/{inis_istasyon_id}/{aktarma_sayisi}/{str(is_halk_tasit_saati).lower()}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            data['HalkTasitSaatiUygulandiMi'] = is_halk_tasit_saati
            return data
        elif response.status_code == 204:
            logger.info(f"'{binis_istasyon_id}' ve '{inis_istasyon_id}' arasında ücret hesaplama için sonuç bulunamadı.")
            return {"hata": "Hesaplama yapılamadı, sonuç bulunamadı."}
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f"İZBAN tutar hesaplama API isteği sırasında hata: {e}")
        return None
    return None


# --- Tool 8: Otobüs Hattı Arama ---
@mcp.tool()
def hat_ara(hat_bilgisi: str, limit: int = 5) -> Optional[List[Dict[str, Any]]]:
    """
    Adında veya güzergahında belirtilen metin geçen otobüs hatlarını arar.
    Sonuç olarak, diğer araçlarda 'line_id' olarak kullanılabilecek 'hat_id' bilgisini de döndürür.

    Args:
        hat_bilgisi (str): Aranacak hat adı, numarası veya güzergah bilgisi.
        limit (int): Döndürülecek maksimum sonuç sayısı.

    Returns:
        Hat bilgilerini ve 'hat_id' içeren kayıtların listesi.
    """
    raw_results = _search_acikveri(
        resource_id=HAT_ARAMA_RESOURCE_ID,
        query=hat_bilgisi,
        limit=limit
    )

    if not raw_results:
        return [] 
    
    processed_results = []
    for record in raw_results:
        if 'HAT_NO' in record:
            clean_record = {
                'hat_no': record.get('HAT_NO'),
                'hat_adi': record.get('ADI'),
                'guzergah': record.get('GUZERGAH'),
                'hat_id_for_iztek_api': record.get('HAT_NO') 
            }
            processed_results.append(clean_record)
    
    return processed_results

# --- Tool 9: Hat Sefer Saati Arama ---
def _indir_ve_cache_le_sefer_saatleri_csv() -> Optional[str]:
    """
    Sefer saatleri CSV dosyasını indirir ve yerel bir kopyasını oluşturur.
    Dosya zaten varsa tekrar indirmez.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    dosya_yolu = os.path.join(script_dir, "data", "eshot-otobus-hareketsaatleri.csv")

    if _download_csv(SEFER_SAATLERI_CSV_URL, dosya_yolu):
        return dosya_yolu
    else:
        logger.warning(f"Sefer saatleri CSV'si indirilemedi. Mevcut dosya (varsa) kullanılacak: '{dosya_yolu}'")
        return dosya_yolu if os.path.exists(dosya_yolu) else None

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
        return [{"hata": "Sefer saatleri verisi indirilemediği için işlem yapılamıyor."}]

    try:
        df = pd.read_csv(dosya_yolu, sep=';')
        hat_verileri = df[df['HAT_NO'] == hat_no].head(limit)

        if hat_verileri.empty:
            return []

        return hat_verileri.to_dict('records')
    except Exception as e:
        logger.error(f"Sefer saatleri CSV dosyası okunurken hata oluştu: {e}")
        return [{"hata": f"Sefer saatleri dosyası işlenirken bir hata oluştu: {e}"}]

# --- Tool 10: Hat Güzergah Koordinatlarını Getir ---
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
    if route_coords_df is None:
        logger.error("Güzergah koordinat verileri yüklenemediği için arama yapılamıyor.")
        return [{"hata": "Güzergah koordinatları veritabanı hazır değil."}]

    results_df = route_coords_df[route_coords_df['HAT_NO'] == hat_no].sort_values('SIRA').head(limit)

    return results_df.to_dict('records')

# --- Tool 11: Hat Detaylarını Ara ---
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

# --- Tool 12: Konuma Göre En Yakın Durakları Bulma ---
@mcp.tool()
def en_yakin_duraklari_bul(latitude: float, longitude: float, limit: int = 5, tur: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
    """
    Verilen enlem ve boylama en yakın otobüs duraklarını veya İZBAN istasyonlarını bulur.
    `tur` parametresi ile sadece belirli bir türdeki yerleri arayabilir.
    Uzaklıkları Haversine formülü kullanarak kilometre cinsinden hesaplar.

    Args:
        latitude (float): Mevcut konumun enlemi.
        longitude (float): Mevcut konumun boylamı.
        limit (int): Döndürülecek maksimum durak/istasyon sayısı.
        tur (str, optional): Aranacak yer türü ('Otobüs Durağı' veya 'İZBAN İstasyonu'). 
                             Belirtilmezse her ikisi de aranır.

    Returns:
        En yakın durakların/istasyonların bilgilerini (tür, ad, mesafe vb.) içeren bir liste.
    """
    if (stops_df is None or stops_df.empty) and \
       (izban_stations_df is None or izban_stations_df.empty):
        logger.error("Durak ve İZBAN istasyon verileri yüklenemediği için arama yapılamıyor.")
        return [{"hata": "Veritabanları hazır değil."}]

    all_locations = []

    if stops_df is not None and not stops_df.empty:
        stops = stops_df.copy()
        stops['TUR'] = 'Otobüs Durağı'
        stops = stops.rename(columns={'DURAK_ADI': 'ADI'})
        all_locations.append(stops[['ADI', 'ENLEM', 'BOYLAM', 'TUR']])

    if izban_stations_df is not None and not izban_stations_df.empty:
        izban = izban_stations_df.copy()
        izban['TUR'] = 'İZBAN İstasyonu'
        izban = izban.rename(columns={'ISTASYON_ADI': 'ADI'})
        all_locations.append(izban[['ADI', 'ENLEM', 'BOYLAM', 'TUR']])

    if not all_locations:
        logger.warning("Konum tabanlı arama için uygun veri bulunamadı.")
        return []

    combined_df = pd.concat(all_locations, ignore_index=True).dropna(subset=['ADI', 'ENLEM', 'BOYLAM'])

    target_df = combined_df
    if tur:
        valid_types = ['Otobüs Durağı', 'İZBAN İstasyonu']
        if tur in valid_types:
            logger.info(f"Arama sadece '{tur}' türündeki yerler için filtreleniyor.")
            target_df = combined_df[combined_df['TUR'] == tur]
        else:
            logger.error(f"Geçersiz tür '{tur}' belirtildi.")
            return [{"hata": f"Geçersiz tür. Sadece {valid_types} değerlerinden biri kullanılabilir."}]
    
    if target_df.empty:
        logger.warning(f"'{tur}' türünde herhangi bir konum bulunamadı.")
        return []

    R = 6371.0

    lat1_rad = np.radians(latitude)
    lon1_rad = np.radians(longitude)
    lat2_rad = np.radians(target_df['ENLEM'])
    lon2_rad = np.radians(target_df['BOYLAM'])

    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad

    a = np.sin(dlat / 2)**2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    distance_km = R * c

    target_df['mesafe_km'] = distance_km

    nearest = target_df.sort_values(by='mesafe_km').head(limit)

    return nearest.to_dict('records')

# --- Tool 13: Tarayıcıdan Hassas Konum Alma ---
@mcp.tool()
def konumumu_al() -> str:
    """
    Kullanıcının hassas coğrafi konumunu almak için yerel bir web sunucusu başlatır.
    Tarayıcıda bir sayfa açar, kullanıcıdan konum izni ister ve alınan koordinatları
    metin olarak döndürür. Bu araç, diğer konum tabanlı araçlarla kullanılabilir.
    """
    location_result = {}
    location_received_event = Event()
    app = Flask(__name__)

    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    log.disabled = True
    app.logger.disabled = True

    @app.route('/')
    def _index():
        return render_template_string(HTML_TEMPLATE_FOR_LOCATION)

    @app.route('/location', methods=['POST'])
    def _receive_location():
        data = request.get_json()
        if data and 'latitude' in data and 'longitude' in data:
            location_result['latitude'] = data['latitude']
            location_result['longitude'] = data['longitude']
            logger.info(f"Tarayıcıdan konum alındı: {data}")
            location_received_event.set()
            request.environ.get('werkzeug.server.shutdown')()
            return jsonify({"status": "success"}), 200
        return jsonify({"status": "error", "message": "Eksik veri"}), 400

    def open_browser():
        webbrowser.open_new("http://127.0.0.1:5000/")

    def run_server():
        with open(os.devnull, 'w') as f, redirect_stdout(f), redirect_stderr(f):
            app.run(port=5000, debug=False, use_reloader=False)

    server_thread = Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()

    logger.info("Konum alma servisi başlatılıyor. Tarayıcı açılacak...")
    Timer(1, open_browser).start()

    received = location_received_event.wait(timeout=60.0)

    if received and 'latitude' in location_result:
        lat = location_result['latitude']
        lon = location_result['longitude']
        return f"Konum başarıyla alındı. Enlem: {lat}, Boylam: {lon}. Bu bilgiyi 'en_yakin_duraklari_bul' gibi araçlarda kullanabilirsiniz."
    else:
        logger.warning("Konum alma zaman aşımına uğradı veya izin verilmedi.")
        return "Konum alınamadı. İşlem 60 saniye içinde zaman aşımına uğradı veya tarayıcıda izin verilmedi."


if __name__ == "__main__":
    mcp.run(transport="stdio")