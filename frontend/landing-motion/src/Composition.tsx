import { AbsoluteFill, Composition, Easing, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig } from 'remotion';
import './style.css';

type Props = { language: 'ar' | 'en' };
type ScreenProps = { src: string; title: string; number: string; opacity: number };

const Screen = ({ src, title, number, opacity }: ScreenProps) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (
    <div className="preview-screen" style={{ opacity }}>
      <Img src={staticFile(src)} className="preview-screenshot" style={{
        scale: interpolate(frame, [0, 6 * fps, 12 * fps], [1, 1.025, 1]),
      }} />
      <div className="preview-caption"><small>{number}</small>{title}</div>
    </div>
  );
};

export const ClinicDay = ({ language }: Props) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const ar = language === 'ar';
  const steps = ar ? ['احجز الموعد', 'افتح ملف المريض', 'وثّق العلاج'] : ['Book the visit', 'Open the patient record', 'Document treatment'];
  return (
    <AbsoluteFill className="preview" dir={ar ? 'rtl' : 'ltr'}>
      <style>{`@font-face { font-family: Cairo; src: url('${staticFile('marketing/fonts/cairo-arabic.woff2')}'); font-weight: 400 900; }`}</style>
      <div className="preview-top"><Img src={staticFile('logo.webp')} /><span>DENTIX / {ar ? 'يوم العيادة، خطوة بخطوة' : 'Your clinic day, in motion'}</span></div>
      <div className="preview-layout">
        <div className="preview-copy" style={{
          opacity: interpolate(frame, [0, .7 * fps], [0, 1], { extrapolateRight: 'clamp' }),
          translate: interpolate(frame, [0, .9 * fps], ['0px 20px', '0px 0px'], { extrapolateRight: 'clamp', easing: Easing.bezier(.16, 1, .3, 1) }),
        }}>
          <p className="preview-eyebrow">{ar ? 'برنامج إدارة عيادات الأسنان' : 'DENTAL CLINIC MANAGEMENT'}</p>
          <h1>{ar ? 'من أول حجز' : 'From the first booking'}<br/><em>{ar ? 'لآخر حساب.' : 'to the final balance.'}</em></h1>
          <p>{ar ? 'رحلة أوضح للمريض. يوم أهدى للعيادة.' : 'A clearer patient journey. A calmer clinic day.'}</p>
          <div className="preview-flow">
            {steps.map((step, index) => (
              <div className="preview-step" key={step} style={{
                opacity: interpolate(frame, [index * .2 * fps, (.7 + index * .2) * fps], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }),
              }}><span>0{index + 1}</span>{step}<i style={{
                scale: interpolate(frame, [index * 4 * fps, (index * 4 + 3.8) * fps, (index * 4 + 4) * fps], [0, 1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }),
              }}/></div>
            ))}
          </div>
        </div>
        <div className="preview-product">
          <div className="preview-browser"><span>● ● ●</span>Dentix / {ar ? 'يوم العيادة' : 'The clinic day'}<b>D</b></div>
          <div className="preview-stage">
            <Screen src={`marketing/screens/dashboard-${language}.webp`} title={steps[0]} number="01" opacity={interpolate(frame, [0, 3.5 * fps, 4 * fps, 11.5 * fps, 12 * fps], [1, 1, 0, 0, 1])} />
            <Screen src={`marketing/screens/patients-${language}.webp`} title={steps[1]} number="02" opacity={interpolate(frame, [0, 3.5 * fps, 4 * fps, 7.5 * fps, 8 * fps, 12 * fps], [0, 0, 1, 1, 0, 0])} />
            <Screen src={`marketing/screens/chart-${language}.webp`} title={steps[2]} number="03" opacity={interpolate(frame, [0, 7.5 * fps, 8 * fps, 11.5 * fps, 12 * fps], [0, 0, 1, 1, 0])} />
          </div>
        </div>
      </div>
      <p className="preview-note">{ar ? 'صور من واجهة Dentix الفعلية، ببيانات تجريبية فقط.' : 'Real Dentix screens. Fictional demonstration data only.'}</p>
    </AbsoluteFill>
  );
};

export const MyComposition = () => (
  <>
    <Composition id="DentixLandingArabic" component={ClinicDay} width={1280} height={800} fps={30} durationInFrames={360} defaultProps={{ language: 'ar' }} />
    <Composition id="DentixLandingEnglish" component={ClinicDay} width={1280} height={800} fps={30} durationInFrames={360} defaultProps={{ language: 'en' }} />
  </>
);
