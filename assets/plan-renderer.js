(function (global) {
    function getMarkdownRenderer() {
        if (typeof global.markdownit !== 'function') {
            throw new Error('markdown-it is not loaded');
        }

        const md = global.markdownit({
            html: false,
            linkify: true,
            typographer: true
        });

        const defaultHeadingOpen = md.renderer.rules.heading_open || function (tokens, idx, options, env, self) {
            return self.renderToken(tokens, idx, options);
        };

        md.renderer.rules.heading_open = function (tokens, idx, options, env, self) {
            const nextToken = tokens[idx + 1];
            const text = nextToken && nextToken.type === 'inline' ? nextToken.content : '';
            const level = Number(tokens[idx].tag.slice(1));

            if (level >= 2 && level <= 3 && text) {
                env.headings = env.headings || [];
                const id = uniqueSlug(text, env.headings);
                tokens[idx].attrSet('id', id);
                env.headings.push({ id: id, text: text, level: level });
            }

            return defaultHeadingOpen(tokens, idx, options, env, self);
        };

        const defaultLinkOpen = md.renderer.rules.link_open || function (tokens, idx, options, env, self) {
            return self.renderToken(tokens, idx, options);
        };

        md.renderer.rules.link_open = function (tokens, idx, options, env, self) {
            tokens[idx].attrSet('target', '_blank');
            tokens[idx].attrSet('rel', 'noopener noreferrer');
            return defaultLinkOpen(tokens, idx, options, env, self);
        };

        return md;
    }

    function uniqueSlug(text, headings) {
        const base = String(text)
            .trim()
            .toLowerCase()
            .replace(/[^\w\u4e00-\u9fa5]+/g, '-')
            .replace(/^-+|-+$/g, '') || 'section';

        let slug = base;
        let counter = 2;
        while (headings.some(function (heading) { return heading.id === slug; })) {
            slug = base + '-' + counter;
            counter += 1;
        }
        return slug;
    }

    function escapeHtml(value) {
        return String(value || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function firstLineTitle(markdown, fallback) {
        const lines = String(markdown || '').split(/\r?\n/);
        for (const line of lines) {
            const match = line.match(/^#\s+(.+)$/);
            if (match) {
                return match[1].trim();
            }
        }
        return fallback || '规划方案';
    }

    function withoutFirstMarkdownTitle(markdown) {
        return String(markdown || '').replace(/^#\s+.+(?:\r?\n|$)/, '');
    }

    function buildMeta(parameters) {
        const mappings = {
            Examination_System: { '1': 'ALEVEL', '2': 'IB', '3': 'AP', '4': '其他' },
            Grade_Range: { '1': 'A*AA-A*A*A*', '2': 'AAB-AAA', '3': 'BBB-ABB', '4': 'CCC-CCD' },
            Strong_Subject_Categ: { '1': '数学计算机', '2': '物理工程地理环境', '3': '经济商科', '4': '生物化学', '5': '人文社科', '6': '其他学科' },
            Planned_Year: { '1': '2026年', '2': '2027年', '3': '2028年', '4': '2029年', '5': '2030年' },
            Study_Region: { '1': '英国', '2': '美国', '3': '加拿大', '4': '澳大利亚', '5': '新加坡', '6': '香港', '7': '新西兰' }
        };

        const p = parameters || {};
        const rows = [
            ['学生', p.Student_Name],
            ['年级', p.Grade ? p.Grade + '年级' : ''],
            ['考试体系', mappings.Examination_System[p.Examination_System] || p.Examination_System],
            ['成绩范围', mappings.Grade_Range[p.Grade_Range] || p.Grade_Range],
            ['优势学科', mappings.Strong_Subject_Categ[p.Strong_Subject_Categ] || p.Strong_Subject_Categ],
            ['计划入学', mappings.Planned_Year[p.Planned_Year] || p.Planned_Year],
            ['留学地区', mappings.Study_Region[p.Study_Region] || p.Study_Region],
            ['目标院校', p.Intended_Institution],
            ['目标专业', p.Intended_Major],
            ['语言状态', p.language_status],
            ['年度预算', p.budget_preference],
            ['城市偏好', p.location_preference]
        ];

        return rows
            .filter(function (row) { return row[1] !== undefined && row[1] !== null && String(row[1]).trim() !== ''; })
            .map(function (row) {
                return '<span class="plan-report__pill"><strong>' + escapeHtml(row[0]) + '</strong>' + escapeHtml(row[1]) + '</span>';
            })
            .join('');
    }

    function buildToc(headings) {
        const visibleHeadings = (headings || []).filter(function (heading) {
            return heading.level === 2;
        });

        if (!visibleHeadings.length) {
            return '';
        }

        return '<nav class="plan-report__toc" aria-label="方案目录">' +
            '<p class="plan-report__toc-title">方案目录</p>' +
            '<ol class="plan-report__toc-list">' +
            visibleHeadings.map(function (heading) {
                return '<li><a href="#' + escapeHtml(heading.id) + '">' + escapeHtml(heading.text) + '</a></li>';
            }).join('') +
            '</ol>' +
            '</nav>';
    }

    function renderReport(markdown, parameters, container, options) {
        if (!container) {
            throw new Error('Missing report container');
        }

        const content = String(markdown || '').trim();
        if (!content) {
            container.innerHTML = '<div class="plan-report"><div class="plan-report__empty">暂无规划方案内容。</div></div>';
            return;
        }

        const md = getMarkdownRenderer();
        const env = { headings: [] };
        const explicitTitle = options && options.title;
        const title = explicitTitle || firstLineTitle(content);
        const bodySource = explicitTitle ? content : withoutFirstMarkdownTitle(content);
        const bodyHtml = md.render(bodySource, env);
        const metaHtml = buildMeta(parameters);
        const tocHtml = buildToc(env.headings);

        container.innerHTML =
            '<section class="plan-report">' +
                '<header class="plan-report__hero">' +
                    '<p class="plan-report__eyebrow">升学规划方案</p>' +
                    '<h1 class="plan-report__title">' + escapeHtml(title) + '</h1>' +
                    '<p class="plan-report__subtitle">以下内容已按正式报告样式排版，原始 Markdown 文件仍可下载保存。</p>' +
                    (metaHtml ? '<div class="plan-report__meta">' + metaHtml + '</div>' : '') +
                '</header>' +
                '<div class="plan-report__layout">' +
                    tocHtml +
                    '<main class="plan-report__content">' +
                        '<article class="plan-report__body">' + bodyHtml + '</article>' +
                    '</main>' +
                '</div>' +
            '</section>';
    }

    global.PlanRenderer = {
        renderReport: renderReport
    };
})(window);
