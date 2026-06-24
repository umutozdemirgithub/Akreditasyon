# Akreditasyon Stüdyosu

Akreditasyon Stüdyosu, rapor yazma ekranını akreditasyon sürecinin ana çalışma alanına dönüştürür. Amaç yalnızca metin üretmek değil; standart beklentilerini kontrol etmek, kanıtları doğru ölçütlerle eşleştirmek, PUKÖ döngüsünü kapatmak, kalite skorunu yükseltmek ve denetime hazır izlenebilir çıktı üretmektir.

## Ana akış

1. Bölüm Haritası üzerinden ana ölçüt veya alt başlık seçilir.
2. Yalnız seçilen kapsama ait kartlar gösterilir.
3. Kart seçildiğinde Aktif Çalışma Alanı açılır.
4. Sağ panelde Akreditasyon Asistanı çalışır.
5. Kullanıcı Standartlara Göre Eksiklik Tarama veya Kanıt Eşleştirme Asistanı işlemlerini başlatır.
6. AI/kurallı analiz öneri üretir; kullanıcı önerileri gözden geçirir ve uygular.

## Yeni akreditasyon odaklı araçlar

### Standartlara Göre Eksiklik Tarama

Seçili başlığı programın akreditasyon profiline göre tarar. Kontrol edilen ana alanlar:

- süreç açıklığı
- doğrudan kanıt
- PUKÖ bütünlüğü
- ölçülebilir sonuç
- paydaş katkısı
- müfredat/program çıktısı ilişkisi
- öğrenci/mezun geri bildirimi
- altyapı yeterliliği
- sürekli iyileştirme izi

Çıktı olarak standart skoru, kritik eksikler, uyarılar, beklenen kanıt türleri ve hızlı düzeltme önerileri verilir.

### Kanıt Eşleştirme Asistanı

Seçili başlığa bağlı kanıtları ölçüt beklentileriyle eşleştirir. Her kanıt için eşleşme skoru, güçlü/zayıf durumu, desteklediği beklentiler ve not/atıf önerisi üretir. Eksik görünen kanıt türleri ayrıca önerilir.

## Backend endpointleri

```text
POST /api/programs/{program_id}/sections/{section_key}/accreditation/gap-scan
POST /api/programs/{program_id}/sections/{section_key}/accreditation/evidence-match
```

## Yetki matrisi

Yeni izinler:

```text
report_studio.standards_scan
report_studio.evidence_match
```

Bu izinler Editör / Hazırlayıcı ve Onaylayıcı için açık, Denetçi (İzleyici) için kapalıdır. Süper Admin, Kurum Admin ve Birim Admin kapsam dahilinde yönetebilir.
