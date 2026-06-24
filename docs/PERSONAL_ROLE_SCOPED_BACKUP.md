# Rol Bazlı Kişisel ZIP Yedek

Bu sürümde her kullanıcı kendi yetki kapsamındaki verileri kendi bilgisayarına ZIP olarak indirebilir.

## Endpointler

- `GET /api/programs/{program_id}/backup/personal.zip`
  - Seçili programda kullanıcının rol/yetki kapsamını indirir.
- `GET /api/me/backup/personal.zip`
  - Kullanıcının erişebildiği tüm programlardaki rol/yetki kapsamını indirir.

## ZIP içeriği

```text
Akreditasyon/Kullanici_Yedegi/
└─ kurum_.../birim_.../bolum_.../program_.../yil_.../id_.../
   ├─ manifest.json
   ├─ 00_metadata/
   ├─ 01_rapor_metni/
   ├─ 02_kanitlar/
   ├─ 03_tablolar/
   ├─ 04_ciktilar/
   ├─ 05_islem_gecmisi/
   └─ 99_raw/scoped_backup.json
```

## Yetki kapsamı

- Editör atanmış başlıkları, bu başlıklara bağlı kanıtları ve tabloları indirir.
- Onaylayıcı, yetkili olduğu programdaki onay kapsamı verilerini indirir.
- Birim/Fakülte/Kurum/Süper Admin kendi yönetim kapsamındaki verileri indirir.
- JSON yedek geri yükleme yönetici işlemi olarak kalır; kişisel ZIP arşiv, kullanıcının bilgisayarına okunabilir arşiv almak içindir.
