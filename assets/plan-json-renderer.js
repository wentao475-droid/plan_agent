(function (global) {
    function escapeHtml(value) {
        return String(value === undefined || value === null ? '' : value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function parsePlan(input) {
        if (!input) {
            return null;
        }
        if (typeof input === 'object') {
            return input;
        }
        try {
            return JSON.parse(String(input).trim());
        } catch (error) {
            return parseFragmentedPlan(String(input));
        }
    }

    function parseFragmentedPlan(input) {
        var text = String(input || '').trim();
        var fragments = [];
        var lines = text.split(/\r?\n/);
        var consumedLines = 0;

        for (var index = 0; index < lines.length; index += 1) {
            var line = lines[index].trim();
            if (!line) {
                consumedLines = index + 1;
                continue;
            }
            if (line.charAt(0) !== '{' && line.charAt(0) !== '[') {
                break;
            }
            try {
                fragments.push(JSON.parse(line));
                consumedLines = index + 1;
            } catch (error) {
                break;
            }
        }

        if (fragments.length < 2) {
            return null;
        }

        var plan = { school_recommend: [], timeline: [], risk_plan: [] };
        var profileKeys = [
            'grade', 'examination_system', 'grade_range', 'strong_subject_categ',
            'planned_year', 'study_region', 'intended_institution', 'intended_major'
        ];

        fragments.forEach(function (fragment) {
            if (Array.isArray(fragment)) {
                var firstObject = fragment.find(function (item) {
                    return item && typeof item === 'object' && !Array.isArray(item);
                });
                if (firstObject && ('school_name' in firstObject || 'program_name' in firstObject)) {
                    plan.school_recommend = fragment;
                } else if (firstObject && ('stage' in firstObject || 'time_range' in firstObject)) {
                    plan.timeline = fragment;
                } else if (firstObject && ('risk' in firstObject || 'impact' in firstObject || 'solution' in firstObject)) {
                    plan.risk_plan = fragment;
                } else if (fragment.every(function (item) { return typeof item === 'string'; })) {
                    plan.missing_fields = fragment;
                }
            } else if (!fragment || typeof fragment !== 'object') {
                return;
            } else if (Array.isArray(fragment.school_recommend)) {
                Object.assign(plan, fragment);
            } else if (fragment.student_profile && typeof fragment.student_profile === 'object') {
                Object.assign(plan, fragment);
            } else if (profileKeys.some(function (key) { return Object.prototype.hasOwnProperty.call(fragment, key); })) {
                plan.student_profile = fragment;
            } else if ('positioning' in fragment || 'strategy' in fragment || 'key_risks' in fragment) {
                plan.summary = fragment;
            } else if ('school_name' in fragment) {
                if (String(fragment.school_name || '').trim()) {
                    plan.school_recommend.push(fragment);
                }
            } else if ('stage' in fragment || 'time_range' in fragment) {
                if (fragment.stage || fragment.time_range || (fragment.tasks || []).length) {
                    plan.timeline.push(fragment);
                }
            } else if ('academic' in fragment || 'language' in fragment || 'activities' in fragment || 'materials' in fragment) {
                plan.bg_suggestion = fragment;
            } else if ('risk' in fragment || 'impact' in fragment || 'solution' in fragment) {
                if (fragment.risk || fragment.impact || fragment.solution) {
                    plan.risk_plan.push(fragment);
                }
            }
        });

        var remainder = lines.slice(consumedLines).join('\n').trim();
        if (remainder) {
            var firstLine = remainder.split(/\r?\n/)[0].trim();
            if (firstLine && !/^(got it|first,|wait,)/i.test(firstLine)) {
                plan.disclaimer = firstLine;
            }
        }

        return plan.student_profile && (plan.summary || plan.bg_suggestion) ? plan : null;
    }

    function listItems(items) {
        const values = Array.isArray(items) ? items.filter(Boolean) : [];
        if (!values.length) {
            return '<p class="json-report__muted">暂无</p>';
        }
        return '<ul>' + values.map(function (item) {
            return '<li>' + escapeHtml(item) + '</li>';
        }).join('') + '</ul>';
    }

    function textOrEmpty(value) {
        const text = String(value || '').trim();
        return text || '未填写';
    }

    function categoryGroups(schools) {
        const labels = [
            { key: 'reach', label: '冲刺' },
            { key: 'match', label: '稳妥' },
            { key: 'safety', label: '保底' }
        ];
        return labels.map(function (item) {
            return {
                key: item.key,
                label: item.label,
                schools: schools.filter(function (school) { return school.category === item.key; })
            };
        });
    }

    function renderMeta(profile) {
        const rows = [
            ['年级', profile.grade],
            ['考试体系', profile.examination_system],
            ['成绩区间', profile.grade_range],
            ['优势学科', profile.strong_subject_categ],
            ['计划入学', profile.planned_year],
            ['留学地区', profile.study_region],
            ['目标院校', profile.intended_institution],
            ['目标专业', profile.intended_major],
            ['学历层次', profile.degree_level],
            ['语言状态', profile.language_status],
            ['年度预算', profile.budget_preference],
            ['城市偏好', profile.location_preference]
        ];

        return rows.filter(function (row) { return row[1]; }).map(function (row) {
            return '<span class="plan-report__pill"><strong>' + escapeHtml(row[0]) + '</strong>' + escapeHtml(row[1]) + '</span>';
        }).join('');
    }

    function renderSchoolCard(school) {
        const requirements = school.requirements || {};
        const score = Number.isFinite(Number(school.match_score)) ? Number(school.match_score) : 0;
        return '<article class="json-school-card json-school-card--' + escapeHtml(school.category || 'default') + '">' +
            '<div class="json-school-card__top">' +
                '<span class="json-school-card__badge">' + escapeHtml(school.category_label || '未分类') + '</span>' +
                '<strong>' + escapeHtml(school.school_name || '未知院校') + '</strong>' +
            '</div>' +
            '<p class="json-school-card__program">' + escapeHtml(textOrEmpty(school.program_name)) + '</p>' +
            '<div class="json-score" aria-label="匹配度">' +
                '<span style="width:' + Math.max(0, Math.min(100, score)) + '%"></span>' +
            '</div>' +
            '<div class="json-school-card__stats">' +
                '<span>匹配度 ' + escapeHtml(score || '-') + '</span>' +
                '<span>录取概率 ' + escapeHtml(textOrEmpty(school.admi_probability)) + '</span>' +
            '</div>' +
            '<p>' + escapeHtml(textOrEmpty(school.reason)) + '</p>' +
            '<dl>' +
                '<div><dt>学术要求</dt><dd>' + escapeHtml(textOrEmpty(requirements.academic)) + '</dd></div>' +
                '<div><dt>语言要求</dt><dd>' + escapeHtml(textOrEmpty(requirements.language)) + '</dd></div>' +
                '<div><dt>背景要求</dt><dd>' + escapeHtml(textOrEmpty(requirements.portfolio_or_extra)) + '</dd></div>' +
            '</dl>' +
        '</article>';
    }

    function renderSchoolGroups(schools) {
        return '<section class="json-report__section" id="schools">' +
            '<div class="json-section-head"><h2>院校推荐</h2><p>按当前 JSON 字段中的 reach / match / safety 分组展示。</p></div>' +
            categoryGroups(schools).map(function (group) {
                return '<div class="json-school-group">' +
                    '<h3>' + escapeHtml(group.label) + '<span>' + group.schools.length + ' 所</span></h3>' +
                    '<div class="json-school-grid">' +
                        (group.schools.length ? group.schools.map(renderSchoolCard).join('') : '<p class="json-report__muted">暂无该分类院校</p>') +
                    '</div>' +
                '</div>';
            }).join('') +
        '</section>';
    }

    function renderComparisonTable(schools) {
        const rows = schools.map(function (school) {
            const requirements = school.requirements || {};
            return '<tr>' +
                '<td><strong>' + escapeHtml(textOrEmpty(school.school_name)) + '</strong><span>' + escapeHtml(textOrEmpty(school.country_or_region)) + '</span></td>' +
                '<td>' + escapeHtml(textOrEmpty(school.program_name)) + '</td>' +
                '<td>' + escapeHtml(textOrEmpty(school.category_label)) + '</td>' +
                '<td>' + escapeHtml(textOrEmpty(school.match_score)) + '</td>' +
                '<td>' + escapeHtml(textOrEmpty(school.admi_probability)) + '</td>' +
                '<td>' + escapeHtml(textOrEmpty(requirements.academic)) + '</td>' +
                '<td>' + escapeHtml((school.risks || []).join('；') || '暂无') + '</td>' +
            '</tr>';
        }).join('');

        return '<section class="json-report__section" id="comparison">' +
            '<div class="json-section-head"><h2>选校对比表</h2><p>用于快速比较录取定位、匹配度和关键要求。</p></div>' +
            '<div class="json-table-wrap">' +
                '<table class="json-comparison-table">' +
                    '<thead><tr><th>院校</th><th>专业</th><th>分类</th><th>匹配度</th><th>录取概率</th><th>学术要求</th><th>风险点</th></tr></thead>' +
                    '<tbody>' + rows + '</tbody>' +
                '</table>' +
            '</div>' +
        '</section>';
    }

    function renderTimeline(timeline) {
        const items = (timeline || []).map(function (stage) {
            return '<article class="json-timeline-item">' +
                '<div><strong>' + escapeHtml(textOrEmpty(stage.stage)) + '</strong><span>' + escapeHtml(textOrEmpty(stage.time_range)) + '</span></div>' +
                listItems(stage.tasks) +
            '</article>';
        }).join('');

        return '<section class="json-report__section" id="timeline">' +
            '<div class="json-section-head"><h2>分阶段时间线</h2><p>把准备动作拆成可执行节点。</p></div>' +
            '<div class="json-timeline">' + (items || '<p class="json-report__muted">暂无时间线</p>') + '</div>' +
        '</section>';
    }

    function renderSuggestions(suggestions) {
        const data = suggestions || {};
        const groups = [
            ['academic', '学术提升'],
            ['language', '语言准备'],
            ['activities', '活动背景'],
            ['materials', '材料准备']
        ];

        return '<section class="json-report__section" id="suggestions">' +
            '<div class="json-section-head"><h2>背景提升建议</h2><p>围绕目标专业补强申请竞争力。</p></div>' +
            '<div class="json-advice-grid">' +
                groups.map(function (group) {
                    return '<article class="json-advice-card"><h3>' + escapeHtml(group[1]) + '</h3>' + listItems(data[group[0]]) + '</article>';
                }).join('') +
            '</div>' +
        '</section>';
    }

    function renderRisks(risks) {
        const rows = (risks || []).map(function (item) {
            return '<article class="json-risk-card">' +
                '<h3>' + escapeHtml(textOrEmpty(item.risk)) + '</h3>' +
                '<p><strong>影响：</strong>' + escapeHtml(textOrEmpty(item.impact)) + '</p>' +
                '<p><strong>方案：</strong>' + escapeHtml(textOrEmpty(item.solution)) + '</p>' +
            '</article>';
        }).join('');

        return '<section class="json-report__section" id="risks">' +
            '<div class="json-section-head"><h2>风险规避策略</h2><p>提前识别申请中最容易卡住的环节。</p></div>' +
            '<div class="json-risk-grid">' + (rows || '<p class="json-report__muted">暂无风险提示</p>') + '</div>' +
        '</section>';
    }

    function renderReport(input, container, options) {
        const data = parsePlan(input);
        if (!container) {
            throw new Error('Missing report container');
        }
        if (!data) {
            container.innerHTML = '<div class="plan-report"><div class="plan-report__empty">JSON 解析失败，无法展示结构化方案。</div></div>';
            return false;
        }

        const profile = data.student_profile || {};
        const summary = data.summary || {};
        const schools = Array.isArray(data.school_recommend) ? data.school_recommend : [];
        const metaHtml = renderMeta(profile);
        const title = (options && options.title) || [profile.intended_institution, profile.intended_major].filter(Boolean).join('_') || '结构化选校方案';
        const schoolCountHint = schools.length === 10 ? '' : '<p class="json-report__warning">当前院校数量为 ' + schools.length + ' 所，建议工作流稳定输出 10 所。</p>';

        container.innerHTML =
            '<section class="plan-report json-report">' +
                '<header class="plan-report__hero">' +
                    '<p class="plan-report__eyebrow">结构化升学规划</p>' +
                    '<h1 class="plan-report__title">' + escapeHtml(title) + '</h1>' +
                    '<p class="plan-report__subtitle">' + escapeHtml(summary.positioning || '已按 JSON 结构生成选校方案，可用于分组展示和对比分析。') + '</p>' +
                    (metaHtml ? '<div class="plan-report__meta">' + metaHtml + '</div>' : '') +
                '</header>' +
                '<div class="plan-report__layout json-report__layout">' +
                    '<nav class="plan-report__toc" aria-label="方案目录">' +
                        '<p class="plan-report__toc-title">方案目录</p>' +
                        '<ol class="plan-report__toc-list">' +
                            '<li><a href="#schools">院校推荐</a></li>' +
                            '<li><a href="#comparison">选校对比表</a></li>' +
                            '<li><a href="#timeline">分阶段时间线</a></li>' +
                            '<li><a href="#suggestions">背景提升建议</a></li>' +
                            '<li><a href="#risks">风险规避策略</a></li>' +
                        '</ol>' +
                    '</nav>' +
                    '<main class="plan-report__content json-report__content">' +
                        '<section class="json-report__summary">' +
                            '<h2>规划策略</h2>' +
                            '<p>' + escapeHtml(summary.strategy || '暂无策略说明') + '</p>' +
                            schoolCountHint +
                            (summary.key_risks && summary.key_risks.length ? '<div class="json-risk-inline"><strong>关键风险</strong>' + listItems(summary.key_risks) + '</div>' : '') +
                        '</section>' +
                        renderSchoolGroups(schools) +
                        renderComparisonTable(schools) +
                        renderTimeline(data.timeline) +
                        renderSuggestions(data.bg_suggestion) +
                        renderRisks(data.risk_plan) +
                        (data.missing_fields && data.missing_fields.length ? '<section class="json-report__section"><div class="json-section-head"><h2>待补充信息</h2></div>' + listItems(data.missing_fields) + '</section>' : '') +
                        (data.disclaimer ? '<p class="json-report__disclaimer">' + escapeHtml(data.disclaimer) + '</p>' : '') +
                    '</main>' +
                '</div>' +
            '</section>';
        return true;
    }

    global.PlanJsonRenderer = {
        parsePlan: parsePlan,
        renderReport: renderReport
    };
})(window);
