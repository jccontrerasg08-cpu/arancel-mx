(() => {
  const language = {
    es: {
      label: 'ES',
      title: 'Búsqueda arancelaria',
      lead: 'Consulta códigos HS, fracciones LIGIE y NICO en la release verificada activa.',
      placeholder: 'Ej. 85171301, teléfonos inteligentes o animales vivos',
      search: 'Buscar',
      verified: 'Datos verificados',
      releaseLabel: 'publicación verificada',
      loading: 'Consultando release verificada…',
      ready: 'Listo para consultar la base verificada.',
      unavailable: 'La búsqueda está temporalmente disponible sólo desde la API.',
      noResults: 'No encontramos resultados para esta consulta.',
      results: 'Resultados verificados',
      api: 'API',
      docs: 'Documentación',
      package: 'PyPI',
      repository: 'Repositorio',
      openApi: 'Abrir ficha en API',
      resultMeta: (item) => `${item.record.level} · ${item.record.dataset_version}`,
      error: 'No fue posible consultar la API verificada. Intenta de nuevo o consulta la documentación.',
    },
    en: {
      label: 'EN',
      title: 'Tariff search',
      lead: 'Search HS codes, LIGIE tariff fractions, and NICO records in the active verified release.',
      placeholder: 'E.g. 85171301, smartphones, or live animals',
      search: 'Search',
      verified: 'Verified data',
      releaseLabel: 'verified release',
      loading: 'Loading verified release…',
      ready: 'Ready to search the verified data service.',
      unavailable: 'Search is temporarily available only from the API.',
      noResults: 'No results matched this query.',
      results: 'Verified results',
      api: 'API',
      docs: 'Documentation',
      package: 'PyPI',
      repository: 'Repository',
      openApi: 'Open API record',
      resultMeta: (item) => `${item.record.level} · ${item.record.dataset_version}`,
      error: 'The verified API could not be reached. Try again or view the documentation.',
    },
  };

  let selectedLanguage = 'es';
  let copy = language[selectedLanguage];

  function element(name, className, text) {
    const node = document.createElement(name);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function navigationLink(label, href) {
    const link = element('a', 'hub-search__link', label);
    link.href = href;
    if (href.startsWith('http')) {
      link.target = '_blank';
      link.rel = 'noreferrer';
    }
    return link;
  }

  function renderResultList(container, results) {
    container.replaceChildren();
    if (!results.length) {
      container.append(element('p', 'hub-search__empty', copy.noResults));
      return;
    }
    const title = element('h2', 'hub-search__results-title', copy.results);
    const list = element('ol', 'hub-search__results');
    results.forEach((item) => {
      const card = element('li', 'hub-search__result');
      const heading = element('p', 'hub-search__code', item.record.code);
      const description = element('p', 'hub-search__description', item.record.description);
      const metadata = element('p', 'hub-search__metadata', copy.resultMeta(item));
      const apiLink = navigationLink(copy.openApi, `/v1/ficha/${encodeURIComponent(item.record.code)}`);
      apiLink.classList.add('hub-search__record-link');
      card.append(heading, description, metadata, apiLink);
      list.append(card);
    });
    container.append(title, list);
  }

  function renderHub() {
    if (document.querySelector('[data-arancel-hub-search]')) return;
    const applicationRoot = document.getElementById('root');
    if (!applicationRoot || !applicationRoot.parentNode) return;

    const panel = element('section', 'hub-search');
    panel.dataset.arancelHubSearch = 'true';
    panel.setAttribute('aria-labelledby', 'hub-search-title');

    const top = element('div', 'hub-search__topline');
    const trust = element('p', 'hub-search__trust', copy.loading);
    trust.setAttribute('role', 'status');
    const languageButton = element('button', 'hub-search__language', 'EN');
    languageButton.type = 'button';
    languageButton.setAttribute('aria-label', 'Switch language');
    top.append(trust, languageButton);

    const title = element('h1', 'hub-search__title', copy.title);
    title.id = 'hub-search-title';
    const lead = element('p', 'hub-search__lead', copy.lead);

    const form = element('form', 'hub-search__form');
    const input = document.createElement('input');
    input.className = 'hub-search__input';
    input.name = 'q';
    input.type = 'search';
    input.autocomplete = 'off';
    input.required = true;
    input.minLength = 1;
    input.placeholder = copy.placeholder;
    input.setAttribute('aria-label', copy.title);
    const submit = element('button', 'hub-search__submit', copy.search);
    submit.type = 'submit';
    form.append(input, submit);

    const links = element('nav', 'hub-search__links');
    links.setAttribute('aria-label', 'Arancel MX resources');
    links.append(
      navigationLink(copy.docs, '/docs'),
      navigationLink(copy.api, '/v1'),
      navigationLink(copy.package, 'https://pypi.org/project/arancel-mx/'),
      navigationLink(copy.repository, 'https://github.com/jccontrerasg08-cpu/arancel-mx'),
    );
    const results = element('div', 'hub-search__result-area');
    results.setAttribute('aria-live', 'polite');
    let releaseMetadata = null;
    panel.append(top, title, lead, form, links, results);
    applicationRoot.parentNode.insertBefore(panel, applicationRoot);

    function applyLanguage() {
      copy = language[selectedLanguage];
      title.textContent = copy.title;
      lead.textContent = copy.lead;
      input.placeholder = copy.placeholder;
      input.setAttribute('aria-label', copy.title);
      submit.textContent = copy.search;
      languageButton.textContent = selectedLanguage === 'es' ? 'EN' : 'ES';
      languageButton.setAttribute('aria-label', selectedLanguage === 'es' ? 'Switch to English' : 'Cambiar a español');
      links.replaceChildren(
        navigationLink(copy.docs, '/docs'),
        navigationLink(copy.api, '/v1'),
        navigationLink(copy.package, 'https://pypi.org/project/arancel-mx/'),
        navigationLink(copy.repository, 'https://github.com/jccontrerasg08-cpu/arancel-mx'),
      );
      results.replaceChildren();
      renderTrust();
    }

    function renderTrust() {
      if (!releaseMetadata) return;
      const verified = releaseMetadata.release_verified && releaseMetadata.structural_valid;
      if (!verified) {
        trust.textContent = copy.unavailable;
        return;
      }
      const publishedAt = releaseMetadata.release_published_at;
      const date = publishedAt ? new Date(publishedAt) : null;
      const locale = selectedLanguage === 'es' ? 'es-MX' : 'en-US';
      const publishedLabel = date && !Number.isNaN(date.valueOf())
        ? ` · ${copy.releaseLabel}: ${new Intl.DateTimeFormat(locale, { dateStyle: 'medium' }).format(date)}`
        : '';
      trust.textContent = `${copy.verified} · ${releaseMetadata.dataset_tag}${publishedLabel}`;
    }

    languageButton.addEventListener('click', () => {
      selectedLanguage = selectedLanguage === 'es' ? 'en' : 'es';
      applyLanguage();
    });

    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const query = input.value.trim();
      if (!query) return;
      submit.disabled = true;
      results.replaceChildren(element('p', 'hub-search__status', copy.loading));
      try {
        const response = await fetch(`/v1/search?q=${encodeURIComponent(query)}&limit=8`);
        if (!response.ok) throw new Error(`search failed with ${response.status}`);
        renderResultList(results, await response.json());
      } catch (error) {
        console.warn('arancel-mx verified search failed', error);
        results.replaceChildren(element('p', 'hub-search__error', copy.error));
      } finally {
        submit.disabled = false;
      }
    });

    fetch("/v1/meta")
      .then((response) => (
        response.ok ? response.json() : Promise.reject(new Error('metadata unavailable'))
      ))
      .then((metadata) => {
        releaseMetadata = metadata;
        renderTrust();
      })
      .catch(() => {
        trust.textContent = copy.unavailable;
      });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', renderHub, { once: true });
  } else {
    renderHub();
  }
})();
