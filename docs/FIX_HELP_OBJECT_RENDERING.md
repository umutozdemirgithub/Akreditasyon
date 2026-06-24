# Yardım & Kullanım React Render Düzeltmesi

## Sorun
`/api/programs/{program_id}/help` yanıtında `workflow` maddeleri `{step, title, detail}` alanlarına sahip nesneler olarak dönüyordu. Frontend bu nesneleri doğrudan React child olarak render etmeye çalıştığı için Yardım & Kullanım ekranında şu hata oluşuyordu:

`Objects are not valid as a React child (found: object with keys {step, title, detail})`

## Düzeltme
- `HelpView` içine güvenli render yardımcıları eklendi: `helpItemKey`, `helpItemText`, `HelpItem`.
- `workflow`, `daily_focus`, `common_rules`, `checklist`, `warnings` ve `modules` alanları string veya nesne olarak gelse de güvenli şekilde yazdırılır hale getirildi.
- İş akışı nesneleri `workflow-card` formatında `step`, `title`, `detail` ayrımıyla gösteriliyor.
- Yardım ekranı aktif role kilitli hale getirildi; diğer rol rehberleri ekranda karışıklık oluşturmuyor.

## Doğrulama
- `python -m pytest tests/test_role_based_help_manual.py -q` geçti.
- `cd frontend && npm run build` geçti.
