import { useState } from 'react';
import Icon from '@/components/ui/icon';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import { toast } from '@/hooks/use-toast';

const STORY_URL  = 'https://functions.poehali.dev/336d7e0c-c72a-414b-993e-e8d6082aaaea';
const PDF_URL    = 'https://functions.poehali.dev/11d8f15e-6fad-41ea-ba16-2fa8cd94d364';
const IMAGES_URL = 'https://functions.poehali.dev/9beafed0-1139-45e4-be53-83c8f41b48aa';

interface Spread {
  heading: string;
  caption: string;
  text: string;
}
interface Story {
  title: string;
  intro: string;
  spreads: Spread[];
}

const BOOK_IMG =
  'https://cdn.poehali.dev/projects/aef6b5b8-e134-4cbc-96a5-cff028092b85/files/5097f0cb-3b34-401f-a99f-5480f63439ed.jpg';

const nav = [
  ['Конструктор', 'builder'],
  ['Шаблоны', 'templates'],
  ['Галерея', 'gallery'],
  ['AI-истории', 'ai'],
  ['Вопросы', 'faq'],
];

const formats = [
  { name: '20×20 см', desc: 'Квадрат', sheets: 'Premium Matte', icon: 'Square' },
  { name: '30×20 см', desc: 'Альбом', sheets: 'Silk 250г', icon: 'RectangleHorizontal' },
  { name: '21×29 см', desc: 'A4 портрет', sheets: 'Fine Art', icon: 'RectangleVertical' },
  { name: '30×30 см', desc: 'Большой квадрат', sheets: 'Lustre 300г', icon: 'Grid2x2' },
];

const templates = [
  { name: 'Свадьба', emoji: '💍', color: 'from-coral/30 to-lemon/20' },
  { name: 'Путешествие', emoji: '✈️', color: 'from-indigo/30 to-coral/20' },
  { name: 'Малыш', emoji: '🍼', color: 'from-lemon/30 to-indigo/20' },
  { name: 'Семья', emoji: '🏡', color: 'from-coral/20 to-indigo/30' },
];

const steps = [
  { icon: 'Upload', title: 'Загрузите фото', text: 'Перетащите снимки — AI сам разложит их по разворотам.' },
  { icon: 'Sparkles', title: 'Опишите историю', text: 'По вашему ТЗ нейросеть напишет тёплые тексты к страницам.' },
  { icon: 'FileCheck2', title: 'Получите PDF', text: 'Готовый макет с полями и обрезкой уходит в типографию.' },
];

const galleryItems = [
  'Семейная хроника · 48 стр.',
  'Балийский дневник · 36 стр.',
  'Первый год Миши · 60 стр.',
  'Наша свадьба · 40 стр.',
  'Год в кадрах · 52 стр.',
];

export default function Index() {
  const [brief, setBrief] = useState('');
  const [format, setFormat] = useState('20x20');
  const [loading, setLoading] = useState(false);
  const [imagesLoading, setImagesLoading] = useState(false);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [story, setStory] = useState<Story | null>(null);
  const [imageUrls, setImageUrls] = useState<(string | null)[]>([]);

  const generate = async () => {
    if (!brief.trim()) {
      toast({ title: 'Опишите вашу историю', description: 'Расскажите, о чём будет книга.' });
      return;
    }
    setLoading(true);
    setStory(null);
    setImageUrls([]);
    try {
      const res = await fetch(STORY_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ brief, spreads: 5 }),
      });
      const data = await res.json();
      if (!res.ok) {
        toast({ title: 'Не удалось сгенерировать', description: data.error || 'Попробуйте позже.' });
        return;
      }
      setStory(data);
      toast({ title: 'История готова!', description: 'Генерируем иллюстрации для разворотов…' });
      setTimeout(() => document.getElementById('layout')?.scrollIntoView({ behavior: 'smooth' }), 100);

      // Запускаем генерацию изображений параллельно
      const bookId = `book_${Date.now()}`;
      setImagesLoading(true);
      fetch(IMAGES_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ spreads: data.spreads, title: data.title, book_id: bookId }),
      })
        .then(r => r.json())
        .then(imgData => {
          if (imgData.image_urls) {
            setImageUrls(imgData.image_urls);
            toast({ title: 'Иллюстрации готовы!', description: 'Все изображения сгенерированы и добавлены в макет.' });
          }
        })
        .catch(() => toast({ title: 'Изображения не загрузились', description: 'Макет будет без иллюстраций.' }))
        .finally(() => setImagesLoading(false));

    } catch {
      toast({ title: 'Ошибка сети', description: 'Проверьте подключение и попробуйте снова.' });
    } finally {
      setLoading(false);
    }
  };

  const downloadPdf = async () => {
    if (!story) return;
    setPdfLoading(true);
    try {
      const res = await fetch(PDF_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ story, format, image_urls: imageUrls }),
      });
      if (!res.ok) {
        const err = await res.json();
        toast({ title: 'Ошибка PDF', description: err.error || 'Попробуйте снова.' });
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `photobook_${format}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
      toast({ title: 'PDF скачан!', description: 'Файл готов для отправки в типографию.' });
    } catch {
      toast({ title: 'Ошибка сети', description: 'Проверьте подключение и попробуйте снова.' });
    } finally {
      setPdfLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0c0a18] text-white font-sans overflow-x-hidden grain">
      {/* glowing blobs */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-40 -left-32 w-[36rem] h-[36rem] bg-coral/25 rounded-full blur-3xl animate-blob" />
        <div className="absolute top-1/3 -right-40 w-[34rem] h-[34rem] bg-indigo/30 rounded-full blur-3xl animate-blob" style={{ animationDelay: '4s' }} />
        <div className="absolute bottom-0 left-1/3 w-[28rem] h-[28rem] bg-lemon/15 rounded-full blur-3xl animate-blob" style={{ animationDelay: '8s' }} />
      </div>

      {/* HEADER */}
      <header className="relative z-20">
        <nav className="container flex items-center justify-between py-6">
          <a href="#" className="font-display font-extrabold text-xl tracking-tight">
            ФОТО<span className="text-gradient">КНИГА</span>
          </a>
          <div className="hidden md:flex items-center gap-8 text-sm text-white/70">
            {nav.map(([label, id]) => (
              <a key={id} href={`#${id}`} className="hover:text-white transition-colors">
                {label}
              </a>
            ))}
          </div>
          <Button className="rounded-full bg-coral hover:bg-coral/90 text-white font-medium px-5">
            Войти
          </Button>
        </nav>
      </header>

      {/* HERO */}
      <section className="relative z-10 container pt-12 pb-24 grid lg:grid-cols-2 gap-12 items-center">
        <div className="animate-fade-in">
          <span className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-4 py-1.5 text-xs text-white/70 mb-6">
            <Icon name="Sparkles" size={14} className="text-lemon" />
            AI-генерация макетов и историй
          </span>
          <h1 className="font-display font-extrabold text-5xl md:text-6xl leading-[1.05] mb-6">
            Ваши фото и <span className="text-gradient">история</span> — в печатной книге
          </h1>
          <p className="text-lg text-white/65 max-w-md mb-8">
            Загрузите снимки, опишите событие — нейросеть соберёт макет и напишет тексты. Готовый PDF уходит прямо в типографию.
          </p>
          <div className="flex flex-wrap gap-4">
            <Button size="lg" className="rounded-full bg-coral hover:bg-coral/90 text-white font-semibold px-8 hover-scale">
              Создать фотокнигу
            </Button>
            <Button size="lg" variant="outline" className="rounded-full border-white/20 bg-transparent text-white hover:bg-white/10 px-8">
              <Icon name="Play" size={16} className="mr-2" /> Как это работает
            </Button>
          </div>
          <div className="flex items-center gap-6 mt-10 text-sm text-white/50">
            <span className="flex items-center gap-2"><Icon name="Check" size={16} className="text-lemon" /> Поля и обрезка</span>
            <span className="flex items-center gap-2"><Icon name="Check" size={16} className="text-lemon" /> PDF для печати</span>
          </div>
        </div>

        <div className="relative animate-fade-in" style={{ animationDelay: '0.2s' }}>
          <div className="absolute -inset-6 bg-gradient-to-tr from-coral/30 to-indigo/30 rounded-[2rem] blur-2xl" />
          <img
            src={BOOK_IMG}
            alt="Макет фотокниги"
            className="relative rounded-[2rem] shadow-2xl border border-white/10 animate-float"
          />
        </div>
      </section>

      {/* STEPS / AI */}
      <section id="ai" className="relative z-10 container py-20">
        <div className="text-center max-w-xl mx-auto mb-14">
          <h2 className="font-display font-bold text-4xl mb-4">Три шага до книги</h2>
          <p className="text-white/60">AI берёт на себя вёрстку и тексты — вам остаётся выбрать лучшие моменты.</p>
        </div>
        <div className="grid md:grid-cols-3 gap-6">
          {steps.map((s, i) => (
            <div
              key={s.title}
              className="group rounded-3xl border border-white/10 bg-white/[0.03] p-8 hover:bg-white/[0.06] transition-colors"
            >
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-coral to-indigo flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                <Icon name={s.icon} size={26} />
              </div>
              <span className="text-xs text-white/40 font-display">0{i + 1}</span>
              <h3 className="font-display font-semibold text-xl mt-1 mb-2">{s.title}</h3>
              <p className="text-white/60 text-sm">{s.text}</p>
            </div>
          ))}
        </div>
      </section>

      {/* BUILDER — AI brief */}
      <section id="builder" className="relative z-10 container py-20">
        <div className="rounded-[2.5rem] border border-white/10 bg-gradient-to-br from-indigo/15 to-coral/10 p-8 md:p-14 grid lg:grid-cols-2 gap-12 items-center">
          <div>
            <span className="text-xs uppercase tracking-widest text-lemon font-display">Конструктор</span>
            <h2 className="font-display font-bold text-4xl mt-3 mb-4">Опишите вашу историю</h2>
            <p className="text-white/60 mb-6">
              Расскажите, о чём книга и какое настроение хотите. AI напишет подписи и тексты для разворотов.
            </p>
            <Textarea
              value={brief}
              onChange={(e) => setBrief(e.target.value)}
              placeholder="Например: книга о нашем путешествии в Грузию, тёплая и душевная, с акцентом на горы и еду…"
              className="min-h-32 rounded-2xl bg-[#0c0a18]/60 border-white/15 text-white placeholder:text-white/30 resize-none"
            />
            <div className="mt-4">
              <p className="text-xs text-white/50 mb-2 font-display uppercase tracking-wider">Формат книги</p>
              <div className="grid grid-cols-2 gap-2">
                {[
                  { val: '20x20', label: '20×20 см', hint: 'Квадрат' },
                  { val: '30x20', label: '30×20 см', hint: 'Альбом' },
                  { val: '21x29', label: '21×29 см', hint: 'A4' },
                  { val: '30x30', label: '30×30 см', hint: 'Большой' },
                ].map((f) => (
                  <button
                    key={f.val}
                    onClick={() => setFormat(f.val)}
                    className={`rounded-xl border px-3 py-2 text-left transition-colors text-sm ${format === f.val ? 'border-lemon bg-lemon/10 text-lemon' : 'border-white/15 bg-white/5 text-white/60 hover:border-white/30'}`}
                  >
                    <span className="font-semibold">{f.label}</span>
                    <span className="block text-xs opacity-70">{f.hint}</span>
                  </button>
                ))}
              </div>
            </div>
            <Button
              onClick={generate}
              disabled={loading}
              className="mt-5 rounded-full bg-lemon hover:bg-lemon/90 text-[#0c0a18] font-semibold px-7 disabled:opacity-60"
            >
              {loading ? (
                <><Icon name="Loader2" size={18} className="mr-2 animate-spin" /> Генерируем…</>
              ) : (
                <><Icon name="Wand2" size={18} className="mr-2" /> Сгенерировать историю</>
              )}
            </Button>
          </div>
          <div className="relative">
            <div className="rounded-3xl bg-[#0c0a18]/70 border border-white/10 p-6 space-y-4">
              <div className="flex items-center gap-2 text-white/40 text-xs">
                <span className="w-3 h-3 rounded-full bg-coral" />
                <span className="w-3 h-3 rounded-full bg-lemon" />
                <span className="w-3 h-3 rounded-full bg-indigo" />
                <span className="ml-2">{story ? story.title : 'Разворот · стр. 4–5'}</span>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="aspect-square rounded-xl bg-gradient-to-br from-coral/40 to-indigo/40" />
                <div className="aspect-square rounded-xl bg-gradient-to-br from-indigo/40 to-lemon/30" />
              </div>
              <p className="text-sm text-white/70 leading-relaxed italic">
                «{story?.spreads?.[0]?.text || 'Дорога вилась вверх, и облака лежали у ног. Здесь, среди гор, время текло иначе…'}»
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* GENERATED LAYOUT */}
      {story && (
        <section id="layout" className="relative z-10 container py-12 animate-fade-in">
          <div className="text-center max-w-2xl mx-auto mb-12">
            <span className="text-xs uppercase tracking-widest text-lemon font-display">Ваш макет</span>
            <h2 className="font-display font-bold text-4xl mt-3 mb-4">{story.title}</h2>
            <p className="text-white/60 italic">{story.intro}</p>
            {imagesLoading && (
              <div className="mt-4 inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-4 py-2 text-sm text-white/60">
                <Icon name="Loader2" size={14} className="animate-spin text-lemon" />
                Генерируем иллюстрации для разворотов…
              </div>
            )}
          </div>
          <div className="space-y-6">
            {story.spreads.map((sp, i) => {
              const imgUrl = imageUrls[i] ?? null;
              return (
                <div
                  key={i}
                  className="rounded-3xl border border-white/10 bg-white/[0.03] p-5 md:p-7 grid md:grid-cols-2 gap-6 items-center"
                >
                  <div className={`${i % 2 ? 'md:order-2' : ''}`}>
                    {imgUrl ? (
                      <img
                        src={imgUrl}
                        alt={sp.heading}
                        className="w-full rounded-2xl object-cover aspect-[4/3] shadow-lg border border-white/10"
                      />
                    ) : (
                      <div className="aspect-[4/3] rounded-2xl bg-gradient-to-br from-coral/30 to-indigo/30 flex items-center justify-center text-white/30 border border-white/10">
                        {imagesLoading
                          ? <Icon name="Loader2" size={32} className="animate-spin text-white/40" />
                          : <Icon name="ImagePlus" size={32} />
                        }
                      </div>
                    )}
                  </div>
                  <div>
                    <span className="text-xs text-white/40 font-display">Разворот {i + 1}</span>
                    <h3 className="font-display font-semibold text-2xl mt-1 mb-3">{sp.heading}</h3>
                    <p className="text-white/70 leading-relaxed mb-3">{sp.text}</p>
                    <p className="text-sm text-lemon/90 italic">{sp.caption}</p>
                  </div>
                </div>
              );
            })}
          </div>
          <div className="mt-10 flex flex-wrap justify-center gap-4">
            <Button
              size="lg"
              onClick={downloadPdf}
              disabled={pdfLoading}
              className="rounded-full bg-coral hover:bg-coral/90 text-white font-semibold px-8 disabled:opacity-60"
            >
              {pdfLoading ? (
                <><Icon name="Loader2" size={18} className="mr-2 animate-spin" /> Формируем PDF…</>
              ) : (
                <><Icon name="FileDown" size={18} className="mr-2" /> Скачать PDF-макет ({format})</>
              )}
            </Button>
            <Button size="lg" variant="outline" className="rounded-full border-white/20 bg-transparent text-white hover:bg-white/10 px-8" onClick={generate} disabled={loading}>
              <Icon name="RefreshCw" size={16} className="mr-2" /> Перегенерировать
            </Button>
          </div>
        </section>
      )}

      {/* TEMPLATES */}
      <section id="templates" className="relative z-10 container py-20">
        <div className="flex items-end justify-between mb-10 flex-wrap gap-4">
          <div>
            <h2 className="font-display font-bold text-4xl mb-2">Шаблоны для старта</h2>
            <p className="text-white/60">Выберите тему — и сразу к загрузке фото.</p>
          </div>
          <Button variant="outline" className="rounded-full border-white/20 bg-transparent text-white hover:bg-white/10">
            Все шаблоны <Icon name="ArrowRight" size={16} className="ml-2" />
          </Button>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {templates.map((t) => (
            <div
              key={t.name}
              className={`group rounded-3xl border border-white/10 bg-gradient-to-br ${t.color} p-6 h-48 flex flex-col justify-between cursor-pointer hover:-translate-y-1 transition-transform`}
            >
              <span className="text-4xl">{t.emoji}</span>
              <div>
                <h3 className="font-display font-semibold text-lg">{t.name}</h3>
                <span className="text-white/60 text-sm flex items-center gap-1">
                  Открыть <Icon name="ArrowUpRight" size={14} className="group-hover:translate-x-0.5 transition-transform" />
                </span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* GALLERY marquee */}
      <section id="gallery" className="relative z-10 py-20">
        <div className="container mb-10">
          <h2 className="font-display font-bold text-4xl mb-2">Галерея примеров</h2>
          <p className="text-white/60">Реальные фотокниги, созданные на платформе.</p>
        </div>
        <div className="relative overflow-hidden">
          <div className="flex gap-6 w-max animate-marquee">
            {[...galleryItems, ...galleryItems].map((label, i) => (
              <div
                key={i}
                className="w-72 shrink-0 rounded-3xl border border-white/10 bg-white/[0.03] overflow-hidden"
              >
                <div className="aspect-[4/3] bg-gradient-to-br from-coral/30 via-indigo/20 to-lemon/20 flex items-center justify-center">
                  <Icon name="BookImage" size={40} className="text-white/40" />
                </div>
                <div className="p-4 text-sm text-white/70">{label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FORMATS / PRINT */}
      <section className="relative z-10 container py-20">
        <div className="text-center max-w-xl mx-auto mb-14">
          <h2 className="font-display font-bold text-4xl mb-4">Форматы и печать</h2>
          <p className="text-white/60">
            Каждый формат — отдельный PDF с правильными полями и обрезкой. Готово к отправке в типографию.
          </p>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {formats.map((f) => (
            <div key={f.name} className="rounded-3xl border border-white/10 bg-white/[0.03] p-6 hover:border-coral/40 transition-colors">
              <div className="w-12 h-12 rounded-xl bg-coral/15 flex items-center justify-center mb-4 text-coral">
                <Icon name={f.icon} size={24} />
              </div>
              <h3 className="font-display font-semibold text-lg">{f.name}</h3>
              <p className="text-white/50 text-sm">{f.desc}</p>
              <p className="text-white/70 text-sm mt-3 flex items-center gap-2">
                <Icon name="Layers" size={14} className="text-lemon" /> {f.sheets}
              </p>
            </div>
          ))}
        </div>
        <div className="mt-10 rounded-3xl border border-white/10 bg-gradient-to-r from-indigo/15 to-coral/15 p-8 flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-white/10 flex items-center justify-center">
              <Icon name="Send" size={26} className="text-lemon" />
            </div>
            <div>
              <h3 className="font-display font-semibold text-xl">Отправка в типографию</h3>
              <p className="text-white/60 text-sm">PDF-макет уходит на печать по почте в один клик.</p>
            </div>
          </div>
          <Button size="lg" className="rounded-full bg-coral hover:bg-coral/90 text-white font-semibold px-8">
            Отправить макет
          </Button>
        </div>
      </section>

      {/* FAQ */}
      <section id="faq" className="relative z-10 container py-20 max-w-3xl">
        <h2 className="font-display font-bold text-4xl mb-10 text-center">Вопросы и ответы</h2>
        <Accordion type="single" collapsible className="space-y-3">
          {[
            ['Как AI создаёт тексты?', 'Вы описываете событие и настроение в конструкторе, а нейросеть пишет подписи и историю для каждого разворота. Тексты можно отредактировать вручную.'],
            ['В каком виде получаю макет?', 'Готовый PDF с соблюдением полей, обрезки и нужного формата — именно так, как требуют типографии.'],
            ['Можно изменить макет вручную?', 'Да, конструктор позволяет менять расположение фото, добавлять страницы и редактировать тексты.'],
            ['Как происходит отправка в печать?', 'Финальный PDF автоматически отправляется в типографию по почте — вам остаётся подтвердить заказ.'],
          ].map(([q, a]) => (
            <AccordionItem key={q} value={q} className="rounded-2xl border border-white/10 bg-white/[0.03] px-5">
              <AccordionTrigger className="text-left font-display font-medium hover:no-underline">{q}</AccordionTrigger>
              <AccordionContent className="text-white/60">{a}</AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </section>

      {/* CTA */}
      <section className="relative z-10 container py-20">
        <div className="rounded-[2.5rem] bg-gradient-to-br from-coral to-indigo p-12 md:p-16 text-center overflow-hidden">
          <h2 className="font-display font-extrabold text-4xl md:text-5xl mb-5">Создайте книгу, которую захочется хранить</h2>
          <p className="text-white/80 max-w-md mx-auto mb-8">Фото, история и печать — в одном месте. Начните бесплатно прямо сейчас.</p>
          <Button size="lg" className="rounded-full bg-white text-[#0c0a18] hover:bg-white/90 font-semibold px-10 hover-scale">
            Создать фотокнигу
          </Button>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="relative z-10 border-t border-white/10">
        <div className="container py-10 flex flex-col md:flex-row items-center justify-between gap-4 text-sm text-white/50">
          <span className="font-display font-extrabold text-white">ФОТО<span className="text-gradient">КНИГА</span></span>
          <span>© 2026 · Сделано с теплом</span>
          <div className="flex gap-5">
            <Icon name="Instagram" size={18} className="hover:text-white transition-colors cursor-pointer" />
            <Icon name="Send" size={18} className="hover:text-white transition-colors cursor-pointer" />
            <Icon name="Mail" size={18} className="hover:text-white transition-colors cursor-pointer" />
          </div>
        </div>
      </footer>
    </div>
  );
}