import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

const config: Config = {
  title: 'arancel-mx',
  tagline: 'Datos arancelarios de México reproducibles, auditables y trazables',
  url: 'https://jccontrerasg08-cpu.github.io',
  baseUrl: '/arancel-mx/',
  organizationName: 'jccontrerasg08-cpu',
  projectName: 'arancel-mx',
  onBrokenLinks: 'throw',
  future: {
    v4: true,
  },
  i18n: {
    defaultLocale: 'es',
    locales: ['es', 'en'],
    localeConfigs: {
      es: {label: 'Español', htmlLang: 'es-MX'},
      en: {label: 'English', htmlLang: 'en-US'},
    },
  },
  presets: [
    [
      'classic',
      {
        docs: {
          path: '../docs',
          routeBasePath: 'docs',
          sidebarPath: './sidebars.ts',
          exclude: ['superpowers/**', 'operations/**'],
          editUrl: 'https://github.com/jccontrerasg08-cpu/arancel-mx/edit/main/docs/',
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],
  themeConfig: {
    colorMode: {
      respectPrefersColorScheme: true,
    },
    navbar: {
      title: 'arancel-mx',
      items: [
        {to: '/', label: 'Inicio', position: 'left'},
        {
          type: 'docSidebar',
          sidebarId: 'publicDocs',
          label: 'Documentación',
          position: 'left',
        },
        {
          href: 'https://github.com/jccontrerasg08-cpu/arancel-mx/releases',
          label: 'Releases',
          position: 'right',
        },
        {
          href: 'https://github.com/jccontrerasg08-cpu/arancel-mx',
          label: 'GitHub',
          position: 'right',
        },
        {type: 'localeDropdown', position: 'right'},
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Proyecto',
          items: [
            {label: 'Primeros pasos', to: '/docs/getting-started'},
            {label: 'Verificar una release', to: '/docs/verify-release'},
            {
              label: 'Contribuir',
              href: 'https://github.com/jccontrerasg08-cpu/arancel-mx/blob/main/CONTRIBUTING.md',
            },
          ],
        },
        {
          title: 'Datos',
          items: [
            {
              label: 'GitHub Releases',
              href: 'https://github.com/jccontrerasg08-cpu/arancel-mx/releases',
            },
            {label: 'Fuentes oficiales', to: '/docs/sources'},
            {label: 'Procedencia', to: '/docs/provenance'},
          ],
        },
      ],
      copyright: `Copyright © ${new Date().getFullYear()} arancel-mx. Apache-2.0.`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
