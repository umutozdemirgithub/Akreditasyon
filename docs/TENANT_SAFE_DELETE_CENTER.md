# Tenant Safe Delete Center

Bu sürümde kurum/tenant silme akışı güvenli kayıt yönetimi merkezine dönüştürüldü.

## Problem

Bir kuruma bağlı program veya kullanıcı varken doğrudan silme işlemi veriyi koparabilir. Önceki davranış bu durumda işlemi durduruyordu.

## Yeni davranış

Tanımlı Kurumlar tablosunda bağlı program veya kullanıcı bulunan bir kurum için Sil butonuna basıldığında güvenli işlem paneli açılır:

1. **Pasifleştir**  
   Kurum ve fakülte kayıtları pasif hale gelir. Programlar ve kullanıcılar korunur.

2. **Bağlı kayıtları taşı**  
   Programlar, program kullanıcı yetkileri, kullanıcılar, bildirimler, export geçmişi ve workflow kayıtları hedef kuruma taşınır. Kaynak kurum arşive alınır.

3. **Kurumla birlikte arşivle**  
   Kurum, fakülte kayıtları, programlar, program yetkileri ve kurum kullanıcıları soft delete/arşiv durumuna alınır. Denetim izi korunur.

Varsayılan kurum kalıcı olarak silinemez. Gerekirse adı düzenlenebilir veya pasifleştirilebilir.
