import type {ReactNode} from 'react';
import clsx from 'clsx';
import Link from '@docusaurus/Link';
import Layout from '@theme/Layout';
import Heading from '@theme/Heading';
import styles from './index.module.css';

const features = [
  {
    title: 'Datos utilizables',
    body: 'CSV, JSON y DuckDB publicados como un contrato verificable de seis assets.',
  },
  {
    title: 'Procedencia verificable',
    body: 'Capturas oficiales, SHA256, tiempos de recuperación y reconciliación legal.',
  },
  {
    title: 'Automatización fail-closed',
    body: 'Un cambio sólo se publica cuando todos los gates de fuente, parser y validación pasan.',
  },
];

function Feature({title, body}: {title: string; body: string}) {
  return (
    <article className={styles.feature}>
      <Heading as="h2">{title}</Heading>
      <p>{body}</p>
    </article>
  );
}

export default function Home(): ReactNode {
  return (
    <Layout
      title="Datos arancelarios de México"
      description="LIGIE, fracciones MX8 y NICO10 con procedencia verificable">
      <main>
        <section className={styles.hero}>
          <div className="container">
            <p className={styles.eyebrow}>Open data · Python · DuckDB</p>
            <Heading as="h1" className={styles.title}>
              arancel-mx
            </Heading>
            <p className={styles.subtitle}>
              Datos arancelarios de México reproducibles, auditables y trazables.
            </p>
            <div className={styles.actions}>
              <Link className="button button--primary button--lg" to="/docs/getting-started">
                Primeros pasos
              </Link>
              <Link className="button button--secondary button--lg" to="/docs/verify-release">
                Verificar una release
              </Link>
            </div>
          </div>
        </section>

        <section className={clsx('container', styles.features)}>
          {features.map((feature) => (
            <Feature key={feature.title} {...feature} />
          ))}
        </section>

        <section className={clsx('container', styles.notice)}>
          <Heading as="h2">Fuente técnica, no asesoría legal</Heading>
          <p>
            El proyecto conserva evidencia y trazabilidad, pero las decisiones jurídicas y de
            clasificación deben contrastarse con las publicaciones oficiales aplicables.
          </p>
        </section>
      </main>
    </Layout>
  );
}
