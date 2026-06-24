import statistics

from datetime import date
from dateutil.relativedelta import relativedelta

from odoo.http import request
from odoo.fields import Domain
from odoo.tools import SQL
from odoo.addons.esg_csrd.controllers.main import EsgCsrdReportController


class EsgCsrdHrReportController(EsgCsrdReportController):
    def _get_valid_employee_version_ids(self, start_date, end_date, is_employee_type=None):
        if is_employee_type:
            employee_type_condition = " AND hv.employee_type = 'employee' "
        elif is_employee_type is False:
            employee_type_condition = " AND hv.employee_type != 'employee' "
        else:
            employee_type_condition = ""

        request.env.cr.execute(SQL(
            """
          SELECT DISTINCT hv.id
            FROM hr_version hv
            JOIN (
                SELECT employee_id, MAX(date_version) AS max_date
                  FROM hr_version
                 WHERE date_version <= %(end_date)s
              GROUP BY employee_id
            ) latest_employee_version
              ON hv.employee_id = latest_employee_version.employee_id
             AND hv.date_version = latest_employee_version.max_date
             AND (hv.departure_date IS NULL OR hv.departure_date >= %(start_date)s)
             AND hv.active = TRUE
             %(employee_type_condition)s
            """,
            start_date=start_date,
            end_date=end_date,
            employee_type_condition=SQL(employee_type_condition),
        ))

        return tuple(row[0] for row in request.env.cr.fetchall())

    def _get_employment_type_data(self, version_ids, total_employees_count):
        data = {
            'employees_full_time_count': 0,
            'employees_full_time_percentage': 0,
            'employees_part_time_count': 0,
            'employees_part_time_percentage': 0,
        }
        if not version_ids:
            return data
        request.env.cr.execute(SQL(
            """
            SELECT COUNT(hv.id)
              FROM hr_version hv, resource_calendar rc
             WHERE hv.id IN %(ids)s
               AND hv.resource_calendar_id = rc.id
               AND rc.hours_per_week = rc.full_time_required_hours
            """,
            ids=version_ids,
        ))
        result = request.env.cr.fetchall()[0][0]
        employees_emp_type_not_reported_count = request.env['hr.version'].sudo().search_count(
            domain=[('id', 'in', version_ids), ('resource_calendar_id', '=', False)],
        )
        employees_part_time_count = total_employees_count - result - employees_emp_type_not_reported_count
        data.update({
            'employees_full_time_count': result,
            'employees_full_time_percentage': round((result / total_employees_count) * 100, 2),
            'employees_part_time_count': employees_part_time_count,
            'employees_part_time_percentage': round((employees_part_time_count / total_employees_count) * 100, 2),
            'employees_emp_type_not_reported_count': employees_emp_type_not_reported_count,
            'employees_emp_type_not_reported_percentage': round((employees_emp_type_not_reported_count / total_employees_count) * 100, 2),
        })
        return data

    def _get_gender_data(self, version_ids, total_employees_count):
        employees_count_per_sex = dict(
            request.env['hr.version'].sudo()._read_group(
                domain=[('id', 'in', version_ids)],
                groupby=['sex'],
                aggregates=['id:count'],
            )
        )
        employees_female_count = employees_count_per_sex.get('female', 0)
        employees_female_percentage = round((employees_female_count / total_employees_count) * 100, 2)
        employees_male_count = employees_count_per_sex.get('male', 0)
        employees_male_percentage = round((employees_male_count / total_employees_count) * 100, 2)
        employees_other_count = employees_count_per_sex.get('other', 0)
        employees_other_percentage = round((employees_other_count / total_employees_count) * 100, 2)
        employees_unknown_count = total_employees_count - employees_female_count - employees_male_count - employees_other_count
        employees_unknown_percentage = round((employees_unknown_count / total_employees_count) * 100, 2)
        return {
            'employees_female_count': employees_female_count,
            'employees_female_percentage': employees_female_percentage,
            'employees_male_count': employees_male_count,
            'employees_male_percentage': employees_male_percentage,
            'employees_other_count': employees_other_count,
            'employees_other_percentage': employees_other_percentage,
            'employees_unknown_count': employees_unknown_count,
            'employees_unknown_percentage': employees_unknown_percentage,
        }

    def _get_age_group_data(self, version_ids, total_employees_count, end_date):
        HrEmployee = request.env['hr.employee']
        date_30_years_ago = end_date - relativedelta(years=30)
        date_50_years_ago = end_date - relativedelta(years=50)
        employees_age_below_30_count = HrEmployee.sudo().search_count(
            domain=Domain([('version_ids', 'in', version_ids), ('birthday', '>', date_30_years_ago)]),
        )
        employees_age_below_30_percentage = round((employees_age_below_30_count / total_employees_count) * 100, 2)
        employees_age_between_30_and_50_count = HrEmployee.sudo().search_count(
            domain=Domain([('version_ids', 'in', version_ids), ('birthday', '<=', date_30_years_ago), ('birthday', '>=', date_50_years_ago)]),
        )
        employees_age_between_30_and_50_percentage = round((employees_age_between_30_and_50_count / total_employees_count) * 100, 2)
        employees_age_above_50_count = HrEmployee.sudo().search_count(
            domain=Domain([('version_ids', 'in', version_ids), ('birthday', '<', date_50_years_ago)]),
        )
        employees_age_above_50_percentage = round((employees_age_above_50_count / total_employees_count) * 100, 2)
        employees_age_unknown_count = total_employees_count - employees_age_below_30_count - employees_age_between_30_and_50_count - employees_age_above_50_count
        employees_age_unknown_percentage = round((employees_age_unknown_count / total_employees_count) * 100, 2)
        return {
            'employees_age_below_30_count': employees_age_below_30_count,
            'employees_age_below_30_percentage': employees_age_below_30_percentage,
            'employees_age_between_30_and_50_count': employees_age_between_30_and_50_count,
            'employees_age_between_30_and_50_percentage': employees_age_between_30_and_50_percentage,
            'employees_age_above_50_count': employees_age_above_50_count,
            'employees_age_above_50_percentage': employees_age_above_50_percentage,
            'employees_age_unknown_count': employees_age_unknown_count,
            'employees_age_unknown_percentage': employees_age_unknown_percentage,
        }

    def _get_contract_type_data(self, version_ids, total_employees_count, start_date, end_date):
        HrVersion = request.env['hr.version']
        employees_permanent_contract_count = HrVersion.sudo().search_count(
            domain=[('id', 'in', version_ids), ('contract_date_start', '<=', end_date), ('contract_date_end', '=', False)]
        )
        employees_permanent_contract_percentage = round((employees_permanent_contract_count / total_employees_count) * 100, 2)
        employees_fixed_term_contract_count = HrVersion.sudo().search_count(
            domain=[('id', 'in', version_ids), ('contract_date_start', '<=', end_date), ('contract_date_end', '>=', start_date)]
        )
        employees_fixed_term_contract_percentage = round((employees_fixed_term_contract_count / total_employees_count) * 100, 2)
        employees_unkown_contract_count = total_employees_count - employees_permanent_contract_count - employees_fixed_term_contract_count
        employees_unkown_contract_percentage = round((employees_unkown_contract_count / total_employees_count) * 100, 2)
        return {
            'employees_permanent_contract_count': employees_permanent_contract_count,
            'employees_permanent_contract_percentage': employees_permanent_contract_percentage,
            'employees_fixed_term_contract_count': employees_fixed_term_contract_count,
            'employees_fixed_term_contract_percentage': employees_fixed_term_contract_percentage,
            'employees_unkown_contract_count': employees_unkown_contract_count,
            'employees_unkown_contract_percentage': employees_unkown_contract_percentage,
        }

    def _get_country_employees_data(self, version_ids):
        if not version_ids:
            return {}
        request.env.cr.execute(SQL(
            """
            SELECT rc.name, COUNT(he.id)
              FROM hr_version hv, hr_employee he, res_partner rp, res_country rc
             WHERE hv.id IN %(ids)s
               AND hv.employee_id = he.id
               AND he.work_contact_id = rp.id
               AND rp.country_id = rc.id
          GROUP BY rc.name
          ORDER BY COUNT(he.id) DESC
            """,
            ids=version_ids,
        ))
        result = request.env.cr.dictfetchall()
        return {
            next(iter(item['name'].values()), ''): item['count']
            for item in result
        }

    def _get_department_employees_data(self, version_ids):
        return dict(
            request.env['hr.version'].sudo()._read_group(
                domain=[('id', 'in', version_ids), ('department_id', '!=', False)],
                groupby=['department_id'],
                aggregates=['__count'],
                order='__count desc',
            )
        )

    def _get_employee_turnover_data(self, start_date, end_date):
        leaving_employees_count = request.env['hr.employee'].sudo().with_context(active_test=False).search_count(
            domain=[
                ('version_ids', 'any', [
                    ('departure_date', '>=', start_date),
                    ('departure_date', '<=', end_date),
                ]),
            ],
        )
        employees_start_year_count = len(self._get_valid_employee_version_ids(start_date, start_date, is_employee_type=True))
        employees_end_year_count = len(self._get_valid_employee_version_ids(end_date, end_date, is_employee_type=True))
        employees_avg_count = (employees_start_year_count + employees_end_year_count) // 2
        employees_turnover_rate = round((leaving_employees_count / employees_avg_count) * 100, 2) if employees_avg_count > 0 else 0
        return {
            'leaving_employees_count': leaving_employees_count,
            'employees_avg_count': employees_avg_count,
            'employees_turnover_rate': employees_turnover_rate,
        }

    def _get_employee_type_data(self, version_ids):
        return dict(
            request.env['hr.version'].sudo()._read_group(
                domain=[('id', 'in', version_ids)],
                groupby=['employee_type'],
                aggregates=['id:count'],
            )
        )

    def _get_employee_tenure_data(self, start_date, end_date, total_employees_count):
        request.env.cr.execute(SQL(
            """
        WITH unique_records AS (
                -- Step 1: Filter by type and handle duplicates
              SELECT DISTINCT
                    employee_id,
                    contract_date_start,
                    COALESCE(contract_date_end, %(end_date)s) AS contract_date_end
                FROM hr_version
               WHERE contract_date_start IS NOT NULL
                 AND employee_type = 'employee'
                 AND date_version <= %(end_date)s
                 AND (departure_date IS NULL OR departure_date >= %(start_date)s)
                 AND active = TRUE
            ),
            employee_tenure AS (
                -- Step 2: Sum duration per employee
              SELECT employee_id,
                     SUM(contract_date_end - contract_date_start) AS total_days
                FROM unique_records
            GROUP BY employee_id
            ),
             tenure_buckets AS (
                -- Step 3: Categorize into tenure ranges
                -- 1 year = 365 days | 3 years = 1095 days | 5 years = 1825 days
              SELECT employee_id,
                     CASE
                         WHEN total_days < 365 THEN 'tenure_lt1'
                         WHEN total_days >= 365 AND total_days < 1095 THEN 'tenure_1_3'
                         WHEN total_days >= 1095 AND total_days <= 1825 THEN 'tenure_3_5'
                         ELSE 'tenure_gt5'
                     END AS tenure_range
                FROM employee_tenure
            )
                -- Step 4: Aggregate counts
              SELECT tenure_range,
                     COUNT(*) AS employee_count
                FROM tenure_buckets
            GROUP BY tenure_range
            """,
            start_date=start_date,
            end_date=end_date,
        ))

        data = {}
        if result := request.env.cr.dictfetchall():
            data = {
                item['tenure_range']: item['employee_count']
                for item in result
            }
        tenure_lt1 = data.get('tenure_lt1', 0)
        tenure_1_3 = data.get('tenure_1_3', 0)
        tenure_3_5 = data.get('tenure_3_5', 0)
        tenure_gt5 = data.get('tenure_gt5', 0)
        tenure_not_reported = total_employees_count - tenure_lt1 - tenure_1_3 - tenure_3_5 - tenure_gt5
        tenure_lt1_pct = round((tenure_lt1 / total_employees_count) * 100, 2)
        tenure_1_3_pct = round((tenure_1_3 / total_employees_count) * 100, 2)
        tenure_3_5_pct = round((tenure_3_5 / total_employees_count) * 100, 2)
        tenure_gt5_pct = round((tenure_gt5 / total_employees_count) * 100, 2)
        tenure_not_reported_pct = round((tenure_not_reported / total_employees_count) * 100, 2)

        return {
            'tenure_lt1': tenure_lt1,
            'tenure_lt1_pct': tenure_lt1_pct,
            'tenure_1_3': tenure_1_3,
            'tenure_1_3_pct': tenure_1_3_pct,
            'tenure_3_5': tenure_3_5,
            'tenure_3_5_pct': tenure_3_5_pct,
            'tenure_gt5': tenure_gt5,
            'tenure_gt5_pct': tenure_gt5_pct,
            'tenure_not_reported': tenure_not_reported,
            'tenure_not_reported_pct': tenure_not_reported_pct,
        }

    def _get_pay_gap_data(self, version_ids):
        versions_by_sex = dict(request.env['hr.version'].sudo()._read_group(
            domain=[('id', 'in', version_ids)],
            groupby=['sex'],
            aggregates=['id:recordset'],
        ))
        male_versions = versions_by_sex.get('male', request.env['hr.version'])
        female_versions = versions_by_sex.get('female', request.env['hr.version'])

        # Normalize wages to a hourly wage
        def get_wages(versions):
            wages = []
            for version in versions:
                if wage := version.sudo()._get_normalized_wage():
                    wages.append(wage)
            return wages

        male_wages = get_wages(male_versions)
        female_wages = get_wages(female_versions)

        male_median = statistics.median(male_wages) if male_wages else 0
        female_median = statistics.median(female_wages) if female_wages else 0
        pay_gap = round((male_median - female_median) / male_median * 100, 2) if male_median and female_median else 0

        return {
            'male_median_hourly_salary': round(male_median, 2),
            'female_median_hourly_salary': round(female_median, 2),
            'pay_gap_percentage': pay_gap,
        }

    def _get_department_pay_gap_data(self, version_ids):
        data = {}
        for department, version_ids in request.env['hr.version'].sudo()._read_group(
            domain=[('id', 'in', version_ids), ('department_id', '!=', False)],
            groupby=['department_id'],
            aggregates=['id:array_agg'],
        ):
            data[department] = self._get_pay_gap_data(version_ids)
        return data

    def _get_contract_type_pay_gap_data(self, version_ids):
        data = {}
        for contract_type, version_ids in request.env['hr.version'].sudo()._read_group(
            domain=[('id', 'in', version_ids), ('contract_type_id', '!=', False)],
            groupby=['contract_type_id'],
            aggregates=['id:array_agg'],
        ):
            data[contract_type] = self._get_pay_gap_data(version_ids)
        return data

    def _get_country_pay_gap_data(self, version_ids):
        data = {}
        for country, version_ids in request.env['hr.version'].sudo()._read_group(
            domain=[('id', 'in', version_ids), ('employee_id.work_contact_id.country_id', '!=', False)],
            groupby=['employee_id.work_contact_id.country_id'],
            aggregates=['id:array_agg'],
        ):
            data[country] = self._get_pay_gap_data(version_ids)
        return data

    def _get_employment_type_per_gender_data(self, version_ids, total_employees_count):
        data = {
            '{{ male_ft_count }}': 0,
            '{{ male_pt_count }}': 0,
            '{{ female_ft_count }}': 0,
            '{{ female_pt_count }}': 0,
            '{{ other_ft_count }}': 0,
            '{{ other_pt_count }}': 0,
            '{{ gender_not_reported_ft_count }}': 0,
            '{{ gender_not_reported_pt_count }}': 0,
        }
        if not version_ids:
            return data
        request.env.cr.execute(SQL(
            """
            SELECT hv.sex, COUNT(hv.id)
              FROM hr_version hv, resource_calendar rc
             WHERE hv.id IN %(ids)s
               AND hv.resource_calendar_id = rc.id
               AND rc.hours_per_week = rc.full_time_required_hours
          GROUP BY hv.sex
            """,
            ids=version_ids,
        ))
        result = request.env.cr.dictfetchall()
        ft_count_per_gender = {
            item['sex']: item['count']
            for item in result
        }
        male_ft_count = ft_count_per_gender.get('male', 0)
        female_ft_count = ft_count_per_gender.get('female', 0)
        other_ft_count = ft_count_per_gender.get('other', 0)
        gender_not_reported_ft_count = ft_count_per_gender.get(None, 0)

        gender_data = self._get_gender_data(version_ids, total_employees_count)
        male_pt_count = gender_data['employees_male_count'] - male_ft_count
        female_pt_count = gender_data['employees_female_count'] - female_ft_count
        other_pt_count = gender_data['employees_other_count'] - other_ft_count
        gender_not_reported_pt_count = gender_data['employees_unknown_count'] - gender_not_reported_ft_count

        data.update({
            'male_ft_count': male_ft_count,
            'male_pt_count': male_pt_count,
            'female_ft_count': female_ft_count,
            'female_pt_count': female_pt_count,
            'other_ft_count': other_ft_count,
            'other_pt_count': other_pt_count,
            'gender_not_reported_ft_count': gender_not_reported_ft_count,
            'gender_not_reported_pt_count': gender_not_reported_pt_count
        })
        return data

    def _get_non_salaried_data(self, version_ids):
        count_per_employee_type = dict(
            request.env['hr.version'].sudo()._read_group(
                domain=[('id', 'in', version_ids)],
                groupby=['employee_type'],
                aggregates=['id:count'],
            )
        )
        return {
            'non_employees_non_salary_count': sum(
                count_per_employee_type.get(emp_type, 0)
                for emp_type in ['student', 'trainee']
            ),
            'non_employees_non_indep_count': sum(
                count_per_employee_type.get(emp_type, 0)
                for emp_type in ['contractor', 'freelance']
            ),
            'non_employees_non_temp_count': count_per_employee_type.get('worker', 0),
        }

    def _get_gender_management_data(self, version_ids):
        if not version_ids:
            return []
        request.env.cr.execute(SQL(
            """
            WITH RECURSIVE leadership_level AS (
                -- 1. Start with employees in the given versions
                SELECT
                    e.id AS employee_id,
                    0 AS level,
                    ARRAY[e.id] AS visited_nodes,
                    hv.sex
                  FROM hr_employee e
                  JOIN hr_version hv ON e.id = hv.employee_id
                 WHERE hv.id IN %(ids)s

                 UNION ALL

                -- 2. Move up the hierarchy
                SELECT
                    e.parent_id AS employee_id,
                    lh.level + 1,
                    lh.visited_nodes || e.parent_id,
                    lh.sex -- Pass the gender of the original employee up the chain
                  FROM hr_employee e
                  JOIN leadership_level lh ON e.id = lh.employee_id
                 WHERE e.parent_id IS NOT NULL
                   AND NOT e.parent_id = ANY(lh.visited_nodes)
            ),
            max_levels AS (
                -- 3. Calculate the maximum level reached for each employee version
                SELECT
                    sex,
                    MAX(level) as max_lvl
                  FROM leadership_level
              GROUP BY employee_id, sex
            )
            -- 4. Count genders per level
            SELECT
                max_lvl,
                sex,
                COUNT(*) as count
              FROM max_levels
          GROUP BY max_lvl, sex
          ORDER BY max_lvl DESC, sex;
            """,
            ids=tuple(version_ids)
        ))
        result = request.env.cr.dictfetchall()

        data = {}
        for item in result:
            lvl = item['max_lvl']
            gender = item['sex']
            count = item['count']
            if lvl not in data:
                data[lvl] = {'male': 0, 'female': 0, 'other': 0}
            if gender:
                data[lvl][gender] += count

        processed_data = []
        for lvl in sorted(data.keys(), reverse=True):
            stats = data[lvl]
            m = stats['male']
            f = stats['female']
            ratio = f / m if m > 0 else 0.0

            processed_data.append({
                'level': lvl,
                'male': m,
                'female': f,
                'other': stats['other'],
                'ratio': round(ratio, 2)
            })
        return processed_data

    def _get_template_variables(self, article):
        template_variables = super()._get_template_variables(article)
        if not (
            request.env.user.has_group('esg.esg_group_manager')
            and request.env.user.has_group('hr.group_hr_user')
            and (esg_report := article.inherited_esg_report_id)
        ):
            return template_variables

        # Reporting Year
        report_version_ids = self._get_valid_employee_version_ids(esg_report.start_date, esg_report.end_date, is_employee_type=True)
        report_total_employees_count = len(report_version_ids)
        template_variables.update({
            '{{ total_reporting }}': str(report_total_employees_count),
            '{{ ft_reporting }}': '',
            '{{ ft_pct_reporting }}': '',
            '{{ pt_reporting }}': '',
            '{{ pt_pct_reporting }}': '',
            '{{ emp_type_not_reported_reporting }}': '',
            '{{ emp_type_not_reported_pct_reporting }}': '',
            '{{ female_reporting }}': '',
            '{{ female_pct_reporting }}': '',
            '{{ male_reporting }}': '',
            '{{ male_pct_reporting }}': '',
            '{{ other_reporting }}': '',
            '{{ other_pct_reporting }}': '',
            '{{ gender_not_reported_reporting }}': '',
            '{{ gender_not_reported_pct_reporting }}': '',
            '{{ age_lt30_reporting }}': '',
            '{{ age_lt30_pct_reporting }}': '',
            '{{ age_30_50_reporting }}': '',
            '{{ age_30_50_pct_reporting }}': '',
            '{{ age_gt50_reporting }}': '',
            '{{ age_gt50_pct_reporting }}': '',
            '{{ age_not_reported_reporting }}': '',
            '{{ age_not_reported_pct_reporting }}': '',
            '{{ permanent_reporting }}': '',
            '{{ permanent_pct_reporting }}': '',
            '{{ fixed_reporting }}': '',
            '{{ fixed_pct_reporting }}': '',
            '{{ contract_not_reported_reporting }}': '',
            '{{ contract_not_reported_pct_reporting }}': '',
            '{{ tenure_lt1_reporting }}': '',
            '{{ tenure_lt1_pct_reporting }}': '',
            '{{ tenure_1_3_reporting }}': '',
            '{{ tenure_1_3_pct_reporting }}': '',
            '{{ tenure_3_5_reporting }}': '',
            '{{ tenure_3_5_pct_reporting }}': '',
            '{{ tenure_gt5_reporting }}': '',
            '{{ tenure_gt5_pct_reporting }}': '',
            '{{ tenure_not_reported_reporting }}': '',
            '{{ tenure_not_reported_pct_reporting }}': '',
            '{{ left_reporting }}': '',
            '{{ avg_emp_reporting }}': '',
            '{{ turnover_reporting }}': '',
            '{{ male_ft_reporting }}': '',
            '{{ male_pt_reporting }}': '',
            '{{ female_ft_reporting }}': '',
            '{{ female_pt_reporting }}': '',
            '{{ other_ft_reporting }}': '',
            '{{ other_pt_reporting }}': '',
            '{{ gender_not_reported_ft_reporting }}': '',
            '{{ gender_not_reported_pt_reporting }}': '',
            '{{ gender_pay_gap_reporting }}': '',
            '{{ median_pay_male_reporting }}': '',
            '{{ median_pay_female_reporting }}': '',
            '{{ total_base }}': '',
            '{{ ft_base }}': '',
            '{{ ft_pct_base }}': '',
            '{{ pt_base }}': '',
            '{{ pt_pct_base }}': '',
            '{{ emp_type_not_reported_base }}': '',
            '{{ emp_type_not_reported_pct_base }}': '',
            '{{ female_base }}': '',
            '{{ female_pct_base }}': '',
            '{{ male_base }}': '',
            '{{ male_pct_base }}': '',
            '{{ other_base }}': '',
            '{{ other_pct_base }}': '',
            '{{ gender_not_reported_base }}': '',
            '{{ gender_not_reported_pct_base }}': '',
            '{{ age_lt30_base }}': '',
            '{{ age_lt30_pct_base }}': '',
            '{{ age_30_50_base }}': '',
            '{{ age_30_50_pct_base }}': '',
            '{{ age_gt50_base }}': '',
            '{{ age_gt50_pct_base }}': '',
            '{{ age_not_reported_base }}': '',
            '{{ age_not_reported_pct_base }}': '',
            '{{ permanent_base }}': '',
            '{{ permanent_pct_base }}': '',
            '{{ fixed_base }}': '',
            '{{ fixed_pct_base }}': '',
            '{{ contract_not_reported_base }}': '',
            '{{ contract_not_reported_pct_base }}': '',
            '{{ tenure_lt1_base }}': '',
            '{{ tenure_lt1_pct_base }}': '',
            '{{ tenure_1_3_base }}': '',
            '{{ tenure_1_3_pct_base }}': '',
            '{{ tenure_3_5_base }}': '',
            '{{ tenure_3_5_pct_base }}': '',
            '{{ tenure_gt5_base }}': '',
            '{{ tenure_gt5_pct_base }}': '',
            '{{ tenure_not_reported_base }}': '',
            '{{ tenure_not_reported_pct_base }}': '',
            '{{ left_base }}': '',
            '{{ avg_emp_base }}': '',
            '{{ turnover_base }}': '',
            '{{ male_ft_base }}': '',
            '{{ male_pt_base }}': '',
            '{{ female_ft_base }}': '',
            '{{ female_pt_base }}': '',
            '{{ other_ft_base }}': '',
            '{{ other_pt_base }}': '',
            '{{ gender_not_reported_ft_base }}': '',
            '{{ gender_not_reported_pt_base }}': '',
            '{{ gender_pay_gap_base }}': '',
            '{{ median_pay_male_base }}': '',
            '{{ median_pay_female_base }}': ''
        })

        # Base Year
        base_total_employees_count = 0
        base_year_start_date = 0
        base_year_end_date = 0
        base_version_ids = False
        has_base_year = esg_report._has_valid_base_year()
        if has_base_year:
            base_year_date = esg_report.company_id.sudo().compute_fiscalyear_dates(date(esg_report.base_year, 1, 1))
            base_year_start_date = base_year_date['date_from']
            base_year_end_date = base_year_date['date_to']
            base_version_ids = self._get_valid_employee_version_ids(base_year_start_date, base_year_end_date, is_employee_type=True)
            base_total_employees_count = len(base_version_ids)
            template_variables['{{ total_base }}'] = str(base_total_employees_count)

        # Data for Table: Employment Type
        # Reporting Year
        if report_version_ids and esg_report.report_type == 'csrd':
            report_employment_type_result = self._get_employment_type_data(report_version_ids, report_total_employees_count)
            template_variables.update({
                '{{ ft_reporting }}': str(report_employment_type_result['employees_full_time_count']),
                '{{ ft_pct_reporting }}': str(report_employment_type_result['employees_full_time_percentage']),
                '{{ pt_reporting }}': str(report_employment_type_result['employees_part_time_count']),
                '{{ pt_pct_reporting }}': str(report_employment_type_result['employees_part_time_percentage']),
                '{{ emp_type_not_reported_reporting }}': str(report_employment_type_result['employees_emp_type_not_reported_count']),
                '{{ emp_type_not_reported_pct_reporting }}': str(report_employment_type_result['employees_emp_type_not_reported_percentage']),
            })
        # Base Year
        if base_version_ids and esg_report.report_type == 'csrd':
            base_employment_type_result = self._get_employment_type_data(base_version_ids, base_total_employees_count)
            template_variables.update({
                '{{ ft_base }}': str(base_employment_type_result['employees_full_time_count']),
                '{{ ft_pct_base }}': str(base_employment_type_result['employees_full_time_percentage']),
                '{{ pt_base }}': str(base_employment_type_result['employees_part_time_count']),
                '{{ pt_pct_base }}': str(base_employment_type_result['employees_part_time_percentage']),
                '{{ emp_type_not_reported_base }}': str(base_employment_type_result['employees_emp_type_not_reported_count']),
                '{{ emp_type_not_reported_pct_base }}': str(base_employment_type_result['employees_emp_type_not_reported_percentage']),
            })

        # Data for Table: Gender
        # Reporting Year
        if report_version_ids:
            report_gender_result = self._get_gender_data(report_version_ids, report_total_employees_count)
            template_variables.update({
                '{{ female_reporting }}': str(report_gender_result['employees_female_count']),
                '{{ female_pct_reporting }}': str(report_gender_result['employees_female_percentage']),
                '{{ male_reporting }}': str(report_gender_result['employees_male_count']),
                '{{ male_pct_reporting }}': str(report_gender_result['employees_male_percentage']),
                '{{ other_reporting }}': str(report_gender_result['employees_other_count']),
                '{{ other_pct_reporting }}': str(report_gender_result['employees_other_percentage']),
                '{{ gender_not_reported_reporting }}': str(report_gender_result['employees_unknown_count']),
                '{{ gender_not_reported_pct_reporting }}': str(report_gender_result['employees_unknown_percentage']),
            })
        # Base Year
        if base_version_ids:
            base_gender_result = self._get_gender_data(base_version_ids, base_total_employees_count)
            template_variables.update({
                '{{ female_base }}': str(base_gender_result['employees_female_count']),
                '{{ female_pct_base }}': str(base_gender_result['employees_female_percentage']),
                '{{ male_base }}': str(base_gender_result['employees_male_count']),
                '{{ male_pct_base }}': str(base_gender_result['employees_male_percentage']),
                '{{ other_base }}': str(base_gender_result['employees_other_count']),
                '{{ other_pct_base }}': str(base_gender_result['employees_other_percentage']),
                '{{ gender_not_reported_base }}': str(base_gender_result['employees_unknown_count']),
                '{{ gender_not_reported_pct_base }}': str(base_gender_result['employees_unknown_percentage']),
            })

        # Data for Table: Age Group
        # Reporting Year
        if report_version_ids:
            report_age_group_result = self._get_age_group_data(report_version_ids, report_total_employees_count, esg_report.end_date)
            template_variables.update({
                '{{ age_lt30_reporting }}': str(report_age_group_result['employees_age_below_30_count']),
                '{{ age_lt30_pct_reporting }}': str(report_age_group_result['employees_age_below_30_percentage']),
                '{{ age_30_50_reporting }}': str(report_age_group_result['employees_age_between_30_and_50_count']),
                '{{ age_30_50_pct_reporting }}': str(report_age_group_result['employees_age_between_30_and_50_percentage']),
                '{{ age_gt50_reporting }}': str(report_age_group_result['employees_age_above_50_count']),
                '{{ age_gt50_pct_reporting }}': str(report_age_group_result['employees_age_above_50_percentage']),
                '{{ age_not_reported_reporting }}': str(report_age_group_result['employees_age_unknown_count']),
                '{{ age_not_reported_pct_reporting }}': str(report_age_group_result['employees_age_unknown_percentage']),
            })
        # Base Year
        if base_version_ids:
            base_age_group_result = self._get_age_group_data(base_version_ids, base_total_employees_count, base_year_end_date)
            template_variables.update({
                '{{ age_lt30_base }}': str(base_age_group_result['employees_age_below_30_count']),
                '{{ age_lt30_pct_base }}': str(base_age_group_result['employees_age_below_30_percentage']),
                '{{ age_30_50_base }}': str(base_age_group_result['employees_age_between_30_and_50_count']),
                '{{ age_30_50_pct_base }}': str(base_age_group_result['employees_age_between_30_and_50_percentage']),
                '{{ age_gt50_base }}': str(base_age_group_result['employees_age_above_50_count']),
                '{{ age_gt50_pct_base }}': str(base_age_group_result['employees_age_above_50_percentage']),
                '{{ age_not_reported_base }}': str(base_age_group_result['employees_age_unknown_count']),
                '{{ age_not_reported_pct_base }}': str(base_age_group_result['employees_age_unknown_percentage']),
            })

        # Data for Table: Contract Type
        # Reporting Year
        if report_version_ids and esg_report.report_type == 'csrd':
            report_contract_type_result = self._get_contract_type_data(report_version_ids, report_total_employees_count, esg_report.start_date, esg_report.end_date)
            template_variables.update({
                '{{ permanent_reporting }}': str(report_contract_type_result['employees_permanent_contract_count']),
                '{{ permanent_pct_reporting }}': str(report_contract_type_result['employees_permanent_contract_percentage']),
                '{{ fixed_reporting }}': str(report_contract_type_result['employees_fixed_term_contract_count']),
                '{{ fixed_pct_reporting }}': str(report_contract_type_result['employees_fixed_term_contract_percentage']),
                '{{ contract_not_reported_reporting }}': str(report_contract_type_result['employees_unkown_contract_count']),
                '{{ contract_not_reported_pct_reporting }}': str(report_contract_type_result['employees_unkown_contract_percentage']),
            })
        # Base Year
        if base_version_ids and esg_report.report_type == 'csrd':
            base_contract_type_result = self._get_contract_type_data(base_version_ids, base_total_employees_count, base_year_start_date, base_year_end_date)
            template_variables.update({
                '{{ permanent_base }}': str(base_contract_type_result['employees_permanent_contract_count']),
                '{{ permanent_pct_base }}': str(base_contract_type_result['employees_permanent_contract_percentage']),
                '{{ fixed_base }}': str(base_contract_type_result['employees_fixed_term_contract_count']),
                '{{ fixed_pct_base }}': str(base_contract_type_result['employees_fixed_term_contract_percentage']),
                '{{ contract_not_reported_base }}': str(base_contract_type_result['employees_unkown_contract_count']),
                '{{ contract_not_reported_pct_base }}': str(base_contract_type_result['employees_unkown_contract_percentage']),
            })

        # Data for Table: Tenure
        # Reporting Year
        if report_version_ids and esg_report.report_type == 'csrd':
            report_employee_tenure_result = self._get_employee_tenure_data(esg_report.start_date, esg_report.end_date, report_total_employees_count)
            template_variables.update({
                '{{ tenure_lt1_reporting }}': str(report_employee_tenure_result['tenure_lt1']),
                '{{ tenure_lt1_pct_reporting }}': str(report_employee_tenure_result['tenure_lt1_pct']),
                '{{ tenure_1_3_reporting }}': str(report_employee_tenure_result['tenure_1_3']),
                '{{ tenure_1_3_pct_reporting }}': str(report_employee_tenure_result['tenure_1_3_pct']),
                '{{ tenure_3_5_reporting }}': str(report_employee_tenure_result['tenure_3_5']),
                '{{ tenure_3_5_pct_reporting }}': str(report_employee_tenure_result['tenure_3_5_pct']),
                '{{ tenure_gt5_reporting }}': str(report_employee_tenure_result['tenure_gt5']),
                '{{ tenure_gt5_pct_reporting }}': str(report_employee_tenure_result['tenure_gt5_pct']),
                '{{ tenure_not_reported_reporting }}': str(report_employee_tenure_result['tenure_not_reported']),
                '{{ tenure_not_reported_pct_reporting }}': str(report_employee_tenure_result['tenure_not_reported_pct']),
            })
        # Base Year
        if base_version_ids and esg_report.report_type == 'csrd':
            base_employee_tenure_result = self._get_employee_tenure_data(base_year_start_date, base_year_end_date, base_total_employees_count)
            template_variables.update({
                '{{ tenure_lt1_base }}': str(base_employee_tenure_result['tenure_lt1']),
                '{{ tenure_lt1_pct_base }}': str(base_employee_tenure_result['tenure_lt1_pct']),
                '{{ tenure_1_3_base }}': str(base_employee_tenure_result['tenure_1_3']),
                '{{ tenure_1_3_pct_base }}': str(base_employee_tenure_result['tenure_1_3_pct']),
                '{{ tenure_3_5_base }}': str(base_employee_tenure_result['tenure_3_5']),
                '{{ tenure_3_5_pct_base }}': str(base_employee_tenure_result['tenure_3_5_pct']),
                '{{ tenure_gt5_base }}': str(base_employee_tenure_result['tenure_gt5']),
                '{{ tenure_gt5_pct_base }}': str(base_employee_tenure_result['tenure_gt5_pct']),
                '{{ tenure_not_reported_base }}': str(base_employee_tenure_result['tenure_not_reported']),
                '{{ tenure_not_reported_pct_base }}': str(base_employee_tenure_result['tenure_not_reported_pct']),
            })

        # Data for Table: Employee Turnover
        # Reporting Year
        if report_version_ids:
            report_employee_turnover_result = self._get_employee_turnover_data(esg_report.start_date, esg_report.end_date)
            template_variables.update({
                '{{ left_reporting }}': str(report_employee_turnover_result['leaving_employees_count']),
                '{{ avg_emp_reporting }}': str(report_employee_turnover_result['employees_avg_count']),
                '{{ turnover_reporting }}': str(report_employee_turnover_result['employees_turnover_rate']),
            })
        # Base Year
        if base_version_ids:
            base_employee_turnover_result = self._get_employee_turnover_data(base_year_start_date, base_year_end_date)
            template_variables.update({
                '{{ left_base }}': str(base_employee_turnover_result['leaving_employees_count']),
                '{{ avg_emp_base }}': str(base_employee_turnover_result['employees_avg_count']),
                '{{ turnover_base }}': str(base_employee_turnover_result['employees_turnover_rate']),
            })

        # Data for Table: Workforce by Type of Contract
        # Reporting Year
        if report_version_ids and esg_report.report_type != 'csrd':
            report_employment_type_per_gender_result = self._get_employment_type_per_gender_data(report_version_ids, report_total_employees_count)
            template_variables.update({
                '{{ male_ft_reporting }}': str(report_employment_type_per_gender_result['male_ft_count']),
                '{{ male_pt_reporting }}': str(report_employment_type_per_gender_result['male_pt_count']),
                '{{ female_ft_reporting }}': str(report_employment_type_per_gender_result['female_ft_count']),
                '{{ female_pt_reporting }}': str(report_employment_type_per_gender_result['female_pt_count']),
                '{{ other_ft_reporting }}': str(report_employment_type_per_gender_result['other_ft_count']),
                '{{ other_pt_reporting }}': str(report_employment_type_per_gender_result['other_pt_count']),
                '{{ gender_not_reported_ft_reporting }}': str(report_employment_type_per_gender_result['gender_not_reported_ft_count']),
                '{{ gender_not_reported_pt_reporting }}': str(report_employment_type_per_gender_result['gender_not_reported_pt_count']),
            })
        # Base Year
        if base_version_ids and esg_report.report_type != 'csrd':
            base_employment_type_per_gender_result = self._get_employment_type_per_gender_data(base_version_ids, base_total_employees_count)
            template_variables.update({
                '{{ male_ft_base }}': str(base_employment_type_per_gender_result['male_ft_count']),
                '{{ male_pt_base }}': str(base_employment_type_per_gender_result['male_pt_count']),
                '{{ female_ft_base }}': str(base_employment_type_per_gender_result['female_ft_count']),
                '{{ female_pt_base }}': str(base_employment_type_per_gender_result['female_pt_count']),
                '{{ other_ft_base }}': str(base_employment_type_per_gender_result['other_ft_count']),
                '{{ other_pt_base }}': str(base_employment_type_per_gender_result['other_pt_count']),
                '{{ gender_not_reported_ft_base }}': str(base_employment_type_per_gender_result['gender_not_reported_ft_count']),
                '{{ gender_not_reported_pt_base }}': str(base_employment_type_per_gender_result['gender_not_reported_pt_count']),
            })

        # Data for Remuneration - Gender Pay Gap
        # Reporting Year
        if report_version_ids and esg_report.report_type != 'csrd':
            report_pay_gap_result = self._get_pay_gap_data(report_version_ids)
            template_variables.update({
                '{{ gender_pay_gap_reporting }}': str(report_pay_gap_result['pay_gap_percentage']),
                '{{ median_pay_male_reporting }}': str(report_pay_gap_result['male_median_hourly_salary']),
                '{{ median_pay_female_reporting }}': str(report_pay_gap_result['female_median_hourly_salary']),
            })
        # Base Year
        if base_version_ids and esg_report.report_type != 'csrd':
            base_pay_gap_result = self._get_pay_gap_data(base_version_ids)
            template_variables.update({
                '{{ gender_pay_gap_base }}': str(base_pay_gap_result['pay_gap_percentage']),
                '{{ median_pay_male_base }}': str(base_pay_gap_result['male_median_hourly_salary']),
                '{{ median_pay_female_base }}': str(base_pay_gap_result['female_median_hourly_salary']),
            })

        # Data for Non-Employees
        # Reporting Year
        report_non_employees_version_ids = self._get_valid_employee_version_ids(esg_report.start_date, esg_report.end_date, is_employee_type=False)
        report_total_non_employees_count = len(report_non_employees_version_ids)
        template_variables.update({
            '{{ total_non_employee_reporting }}': str(report_total_non_employees_count),
            '{{ total_non_employee_base }}': '',
            '{{ non_employee_female_reporting }}': '',
            '{{ non_employee_female_pct_reporting }}': '',
            '{{ non_employee_male_reporting }}': '',
            '{{ non_employee_male_pct_reporting }}': '',
            '{{ non_employee_other_reporting }}': '',
            '{{ non_employee_other_pct_reporting }}': '',
            '{{ non_employee_gender_not_reported_reporting }}': '',
            '{{ non_employee_gender_not_reported_pct_reporting }}': '',
            '{{ non_salary_reporting }}': '',
            '{{ non_indep_reporting }}': '',
            '{{ non_temp_reporting }}': '',
            '{{ non_employee_female_base }}': '',
            '{{ non_employee_female_pct_base }}': '',
            '{{ non_employee_male_base }}': '',
            '{{ non_employee_male_pct_base }}': '',
            '{{ non_employee_other_base }}': '',
            '{{ non_employee_other_pct_base }}': '',
            '{{ non_employee_gender_not_reported_base }}': '',
            '{{ non_employee_gender_not_reported_pct_base }}': '',
            '{{ non_salary_base }}': '',
            '{{ non_indep_base }}': '',
            '{{ non_temp_base }}': '',
        })
        # Base Year
        base_total_non_employees_count = 0
        base_non_employees_version_ids = False
        if has_base_year:
            base_non_employees_version_ids = self._get_valid_employee_version_ids(base_year_start_date, base_year_end_date, is_employee_type=False)
            base_total_non_employees_count = len(base_non_employees_version_ids)
            template_variables['{{ total_non_employee_base }}'] = str(base_total_non_employees_count)

        # Data for Table: Gender (Non-Employees)
        # Reporting Year
        if report_non_employees_version_ids and esg_report.report_type == 'csrd':
            non_employees_report_gender_result = self._get_gender_data(report_non_employees_version_ids, report_total_non_employees_count)
            template_variables.update({
                '{{ non_employee_female_reporting }}': str(non_employees_report_gender_result['employees_female_count']),
                '{{ non_employee_female_pct_reporting }}': str(non_employees_report_gender_result['employees_female_percentage']),
                '{{ non_employee_male_reporting }}': str(non_employees_report_gender_result['employees_male_count']),
                '{{ non_employee_male_pct_reporting }}': str(non_employees_report_gender_result['employees_male_percentage']),
                '{{ non_employee_other_reporting }}': str(non_employees_report_gender_result['employees_other_count']),
                '{{ non_employee_other_pct_reporting }}': str(non_employees_report_gender_result['employees_other_percentage']),
                '{{ non_employee_gender_not_reported_reporting }}': str(non_employees_report_gender_result['employees_unknown_count']),
                '{{ non_employee_gender_not_reported_pct_reporting }}': str(non_employees_report_gender_result['employees_unknown_percentage']),
            })
        # Base Year
        if base_non_employees_version_ids and esg_report.report_type == 'csrd':
            non_employees_base_gender_result = self._get_gender_data(base_non_employees_version_ids, base_total_non_employees_count)
            template_variables.update({
                '{{ non_employee_female_base }}': str(non_employees_base_gender_result['employees_female_count']),
                '{{ non_employee_female_pct_base }}': str(non_employees_base_gender_result['employees_female_percentage']),
                '{{ non_employee_male_base }}': str(non_employees_base_gender_result['employees_male_count']),
                '{{ non_employee_male_pct_base }}': str(non_employees_base_gender_result['employees_male_percentage']),
                '{{ non_employee_other_base }}': str(non_employees_base_gender_result['employees_other_count']),
                '{{ non_employee_other_pct_base }}': str(non_employees_base_gender_result['employees_other_percentage']),
                '{{ non_employee_gender_not_reported_base }}': str(non_employees_base_gender_result['employees_unknown_count']),
                '{{ non_employee_gender_not_reported_pct_base }}': str(non_employees_base_gender_result['employees_unknown_percentage']),
            })

        # Data for Table: B8.5: Non-Employees
        # Reporting Year
        if report_non_employees_version_ids and esg_report.report_type != 'csrd':
            non_employees_report_non_salaried_result = self._get_non_salaried_data(report_non_employees_version_ids)
            template_variables.update({
                '{{ non_salary_reporting }}': str(non_employees_report_non_salaried_result['non_employees_non_salary_count']),
                '{{ non_indep_reporting }}': str(non_employees_report_non_salaried_result['non_employees_non_indep_count']),
                '{{ non_temp_reporting }}': str(non_employees_report_non_salaried_result['non_employees_non_temp_count']),
            })
        # Base Year
        if base_non_employees_version_ids and esg_report.report_type != 'csrd':
            non_employees_base_non_salaried_result = self._get_non_salaried_data(base_non_employees_version_ids)
            template_variables.update({
                '{{ non_salary_base }}': str(non_employees_base_non_salaried_result['non_employees_non_salary_count']),
                '{{ non_indep_base }}': str(non_employees_base_non_salaried_result['non_employees_non_indep_count']),
                '{{ non_temp_base }}': str(non_employees_base_non_salaried_result['non_employees_non_temp_count']),
            })

        # Data for Employees + Non-Employees
        report_all_version_ids = self._get_valid_employee_version_ids(esg_report.start_date, esg_report.end_date)
        report_total_all_count = len(report_all_version_ids)
        template_variables.update({
            '{{ women_workforce_pct_reporting }}': '',
            '{{ women_management_pct_reporting }}': '',
            '{{ employees_lt30_pct_reporting }}': '',
            '{{ employees_gt50_pct_reporting }}': '',
        })

        # Data for Table: Diversity Metrics
        if report_all_version_ids and esg_report.report_type == 'csrd':
            report_gender_result = self._get_gender_data(report_all_version_ids, report_total_all_count)
            template_variables.update({
                '{{ women_workforce_pct_reporting }}': str(report_gender_result['employees_female_percentage']),
            })
            report_age_group_result = self._get_age_group_data(report_all_version_ids, report_total_all_count, esg_report.end_date)
            template_variables.update({
                '{{ employees_lt30_pct_reporting }}': str(report_age_group_result['employees_age_below_30_percentage']),
                '{{ employees_gt50_pct_reporting }}': str(report_age_group_result['employees_age_above_50_percentage']),
            })
            report_gender_management_data = self._get_gender_management_data(report_all_version_ids)
            if report_gender_management_data:
                total = report_gender_management_data[0]['female'] + report_gender_management_data[0]['male']
                template_variables['{{ women_management_pct_reporting }}'] = str(round((report_gender_management_data[0]['female'] / total) * 100, 2)) if total > 0 else '0.0'

        return template_variables

    def _get_html_template_variables(self, article):
        html_template_variables = super()._get_html_template_variables(article)
        if not (
            request.env.user.has_group('esg.esg_group_manager')
            and request.env.user.has_group('hr.group_hr_user')
            and (esg_report := article.inherited_esg_report_id)
        ):
            return html_template_variables

        # Reporting Year
        report_version_ids = self._get_valid_employee_version_ids(esg_report.start_date, esg_report.end_date, is_employee_type=True)
        report_total_employees_count = len(report_version_ids)
        html_template_variables.update({
            '{{ country_employees_table }}': '',
            '{{ department_employees_table }}': '',
        })

        # Base Year
        base_total_employees_count = 0
        base_year_start_date = 0
        base_year_end_date = 0
        base_version_ids = False
        has_base_year = esg_report._has_valid_base_year()
        if has_base_year:
            base_year_date = esg_report.company_id.sudo().compute_fiscalyear_dates(date(esg_report.base_year, 1, 1))
            base_year_start_date = base_year_date['date_from']
            base_year_end_date = base_year_date['date_to']
            base_version_ids = self._get_valid_employee_version_ids(base_year_start_date, base_year_end_date, is_employee_type=True)
            base_total_employees_count = len(base_version_ids)

        # Data for Table: Geography/Region
        # Reporting Year
        if report_version_ids:
            report_country_data = self._get_country_employees_data(report_version_ids)
            # Base Year
            base_country_data = self._get_country_employees_data(base_version_ids)
            rows = []
            for report_country_name, report_country_count in report_country_data.items():
                base_country_count = base_country_data.get(report_country_name, 0) if base_version_ids else ''
                base_country_percentage = round((base_country_count / base_total_employees_count) * 100, 2) if base_version_ids and base_total_employees_count > 0 else ''
                rows.append({
                    'name': report_country_name,
                    'r_count': report_country_count,
                    'r_pct': round((report_country_count / report_total_employees_count) * 100, 2),
                    'b_count': base_country_count,
                    'b_pct': base_country_percentage,
                })
            for base_country_name, base_country_count in base_country_data.items():
                if base_country_name in report_country_data:
                    continue
                rows.append({
                    'name': base_country_name,
                    'r_count': 0,
                    'r_pct': 0.0,
                    'b_count': base_country_count,
                    'b_pct': round((base_country_count / base_total_employees_count) * 100, 2) if base_total_employees_count > 0 else '',
                })
            rows.extend([
                {
                    'name': 'Not Reported',
                    'r_count': report_total_employees_count - sum(report_country_data.values()),
                    'r_pct': round(((report_total_employees_count - sum(report_country_data.values())) / report_total_employees_count) * 100, 2) if report_total_employees_count > 0 else 0,
                    'b_count': base_total_employees_count - sum(base_country_data.values()) if base_version_ids else '',
                    'b_pct': round(((base_total_employees_count - sum(base_country_data.values())) / base_total_employees_count) * 100, 2) if base_version_ids and base_total_employees_count > 0 else '',
                },
                {
                    'name': 'Total Employees',
                    'r_count': report_total_employees_count,
                    'r_pct': '100',
                    'b_count': base_total_employees_count or '',
                    'b_pct': '100' if base_total_employees_count > 0 else '',
                },
            ])
            employees_number_per_country_table = request.env['ir.qweb']._render('esg_csrd_hr.esg_csrd_hr_report_country_employees_table', {
                'rows': rows,
                'has_base_year': has_base_year,
            })
            html_template_variables['{{ country_employees_table }}'] = employees_number_per_country_table

        # Data for Table: Job Category/Function
        # Reporting Year
        if report_version_ids and esg_report.report_type == 'csrd':
            report_department_data = self._get_department_employees_data(report_version_ids)
            # Base Year
            base_department_data = self._get_department_employees_data(base_version_ids)
            rows = []
            for report_department, report_count in report_department_data.items():
                base_count = base_department_data.get(report_department, 0) if base_version_ids else ''
                base_percentage = round((base_count / base_total_employees_count) * 100, 2) if base_version_ids and base_total_employees_count > 0 else ''
                rows.append({
                    'name': report_department.name,
                    'r_count': report_count,
                    'r_pct': round((report_count / report_total_employees_count) * 100, 2),
                    'b_count': base_count,
                    'b_pct': base_percentage,
                })
            for base_department, base_count in base_department_data.items():
                if base_department in report_department_data:
                    continue
                rows.append({
                    'name': base_department.name,
                    'r_count': 0,
                    'r_pct': 0.0,
                    'b_count': base_count,
                    'b_pct': round((base_count / base_total_employees_count) * 100, 2) if base_total_employees_count > 0 else '',
                })
            rows.extend([
                {
                    'name': 'Not Reported',
                    'r_count': report_total_employees_count - sum(report_department_data.values()),
                    'r_pct': round(((report_total_employees_count - sum(report_department_data.values())) / report_total_employees_count) * 100, 2) if report_total_employees_count > 0 else 0,
                    'b_count': base_total_employees_count - sum(base_department_data.values()) if base_version_ids else '',
                    'b_pct': round(((base_total_employees_count - sum(base_department_data.values())) / base_total_employees_count) * 100, 2) if base_version_ids and base_total_employees_count > 0 else '',
                },
                {
                    'name': 'Total Employees',
                    'r_count': report_total_employees_count,
                    'r_pct': '100',
                    'b_count': base_total_employees_count or '',
                    'b_pct': '100' if base_total_employees_count > 0 else '',
                },
            ])
            employees_number_per_department_table = request.env['ir.qweb']._render('esg_csrd_hr.esg_csrd_hr_report_department_employees_table', {
                'rows': rows,
                'has_base_year': has_base_year,
            })
            html_template_variables['{{ department_employees_table }}'] = employees_number_per_department_table

        # Data for Non-Employees
        # Reporting Year
        report_non_employees_version_ids = self._get_valid_employee_version_ids(esg_report.start_date, esg_report.end_date, is_employee_type=False)
        report_total_non_employees_count = len(report_non_employees_version_ids)
        html_template_variables.update({
            '{{ total_non_employee_reporting }}': str(report_total_non_employees_count),
            '{{ non_employees_types_table }}': '',
            '{{ country_non_employees_table }}': '',
            '{{ department_non_employees_table }}': '',
        })
        # Base Year
        base_total_non_employees_count = 0
        base_non_employees_version_ids = False
        if has_base_year:
            base_non_employees_version_ids = self._get_valid_employee_version_ids(base_year_start_date, base_year_end_date, is_employee_type=False)
            base_total_non_employees_count = len(base_non_employees_version_ids)
            html_template_variables['{{ total_non_employee_base }}'] = str(base_total_non_employees_count)

        # Data for Table: Employment Type (Non-Employees)
        if report_non_employees_version_ids and esg_report.report_type == 'csrd':
            report_non_employee_type_data = self._get_employee_type_data(report_non_employees_version_ids)
            base_non_employee_type_data = self._get_employee_type_data(base_non_employees_version_ids)
            rows = []
            employee_type_labels = dict(request.env['hr.version']._fields['employee_type']._description_selection(request.env))
            for employee_type, count in report_non_employee_type_data.items():
                base_count = base_non_employee_type_data.get(employee_type, 0) if base_non_employees_version_ids else ''
                employee_type_label = employee_type_labels.get(employee_type)
                rows.append({
                    'name': employee_type_label,
                    'r_count': count,
                    'r_pct': round((count / report_total_non_employees_count) * 100, 2),
                    'b_count': base_count,
                    'b_pct': round((base_count / base_total_non_employees_count) * 100, 2) if base_total_non_employees_count > 0 else '',
                })
            for employee_type, count in base_non_employee_type_data.items():
                if employee_type in report_non_employee_type_data:
                    continue
                employee_type_label = employee_type_labels.get(employee_type)
                rows.append({
                    'name': employee_type_label,
                    'r_count': 0,
                    'r_pct': 0.0,
                    'b_count': count,
                    'b_pct': round((count / base_total_non_employees_count) * 100, 2) if base_total_non_employees_count > 0 else '',
                })
            rows.append({
                'name': 'Total Non-Employees',
                'r_count': report_total_non_employees_count,
                'r_pct': '100',
                'b_count': base_total_non_employees_count or '',
                'b_pct': '100' if base_total_non_employees_count > 0 else '',
            })
            non_employees_types_table = request.env['ir.qweb']._render('esg_csrd_hr.esg_csrd_hr_report_type_non_employees_table', {
                'rows': rows,
                'has_base_year': has_base_year,
            })
            html_template_variables['{{ non_employees_types_table }}'] = non_employees_types_table

        # Data for Table: Geography/Region (Non-Employees)
        # Reporting Year
        if report_non_employees_version_ids and esg_report.report_type == 'csrd':
            report_country_data = self._get_country_employees_data(report_non_employees_version_ids)
            # Base Year
            base_country_data = self._get_country_employees_data(base_non_employees_version_ids)
            rows = []
            for report_country_name, report_country_count in report_country_data.items():
                base_country_count = base_country_data.get(report_country_name, 0) if base_non_employees_version_ids else ''
                base_country_percentage = round((base_country_count / base_total_non_employees_count) * 100, 2) if base_non_employees_version_ids and base_total_non_employees_count > 0 else ''
                rows.append({
                    'name': report_country_name,
                    'r_count': report_country_count,
                    'r_pct': round((report_country_count / report_total_non_employees_count) * 100, 2),
                    'b_count': base_country_count,
                    'b_pct': base_country_percentage,
                })
            for base_country_name, base_country_count in base_country_data.items():
                if base_country_name in report_country_data:
                    continue
                rows.append({
                    'name': base_country_name,
                    'r_count': 0,
                    'r_pct': 0.0,
                    'b_count': base_country_count,
                    'b_pct': round((base_country_count / base_total_non_employees_count) * 100, 2) if base_total_non_employees_count > 0 else '',
                })
            rows.extend([
                {
                    'name': 'Not Reported',
                    'r_count': report_total_non_employees_count - sum(report_country_data.values()),
                    'r_pct': round(((report_total_non_employees_count - sum(report_country_data.values())) / report_total_non_employees_count) * 100, 2) if report_total_non_employees_count > 0 else 0,
                    'b_count': base_total_non_employees_count - sum(base_country_data.values()) if base_non_employees_version_ids else '',
                    'b_pct': round(((base_total_non_employees_count - sum(base_country_data.values())) / base_total_non_employees_count) * 100, 2) if base_non_employees_version_ids and base_total_non_employees_count > 0 else '',
                },
                {
                    'name': 'Total Non-Employees',
                    'r_count': report_total_non_employees_count,
                    'r_pct': '100',
                    'b_count': base_total_non_employees_count or '',
                    'b_pct': '100' if base_total_non_employees_count > 0 else '',
                },
            ])
            country_non_employees_table = request.env['ir.qweb']._render('esg_csrd_hr.esg_csrd_hr_report_department_non_employees_table', {
                'rows': rows,
                'has_base_year': has_base_year,
            })
            html_template_variables['{{ country_non_employees_table }}'] = country_non_employees_table

        # Data for Table: Job Category/Function (Non-Employees)
        # Reporting Year
        if report_non_employees_version_ids and esg_report.report_type == 'csrd':
            report_department_data = self._get_department_employees_data(report_non_employees_version_ids)
            # Base Year
            base_department_data = self._get_department_employees_data(base_non_employees_version_ids)
            rows = []
            for report_department, report_count in report_department_data.items():
                base_count = base_department_data.get(report_department, 0) if base_non_employees_version_ids else ''
                base_percentage = round((base_count / base_total_non_employees_count) * 100, 2) if base_non_employees_version_ids and base_total_non_employees_count > 0 else ''
                rows.append({
                    'name': report_department.name,
                    'r_count': report_count,
                    'r_pct': round((report_count / report_total_non_employees_count) * 100, 2),
                    'b_count': base_count,
                    'b_pct': base_percentage,
                })
            for base_department, base_count in base_department_data.items():
                if base_department in report_department_data:
                    continue
                rows.append({
                    'name': base_department.name,
                    'r_count': 0,
                    'r_pct': 0.0,
                    'b_count': base_count,
                    'b_pct': round((base_count / base_total_non_employees_count) * 100, 2) if base_total_non_employees_count > 0 else '',
                })
            rows.extend([
                {
                    'name': 'Not Reported',
                    'r_count': report_total_non_employees_count - sum(report_department_data.values()),
                    'r_pct': round(((report_total_non_employees_count - sum(report_department_data.values())) / report_total_non_employees_count) * 100, 2) if report_total_non_employees_count > 0 else 0,
                    'b_count': base_total_non_employees_count - sum(base_department_data.values()) if base_non_employees_version_ids else '',
                    'b_pct': round(((base_total_non_employees_count - sum(base_department_data.values())) / base_total_non_employees_count) * 100, 2) if base_non_employees_version_ids and base_total_non_employees_count > 0 else '',
                },
                {
                    'name': 'Total Non-Employees',
                    'r_count': report_total_non_employees_count,
                    'r_pct': '100',
                    'b_count': base_total_non_employees_count or '',
                    'b_pct': '100' if base_total_non_employees_count > 0 else '',
                },
            ])
            department_non_employees_table = request.env['ir.qweb']._render('esg_csrd_hr.esg_csrd_hr_report_department_non_employees_table', {
                'rows': rows,
                'has_base_year': has_base_year,
            })
            html_template_variables['{{ department_non_employees_table }}'] = department_non_employees_table

        # Data for Employees + Non-Employees
        # Reporting Year
        report_all_version_ids = self._get_valid_employee_version_ids(esg_report.start_date, esg_report.end_date)
        html_template_variables.update({
            '{{ department_all_employees_pay_gap_table }}': '',
            '{{ contract_type_all_employees_pay_gap_table }}': '',
            '{{ country_all_employees_pay_gap_table }}': '',
            '{{ management_level_gender_table }}': '',
        })

        # Data for Tables: Remuneration Metrics
        # Data for Table: Job Category/Function Pay Gap (Employees + Non-Employees)
        # Reporting Year
        if report_all_version_ids and esg_report.report_type == 'csrd':
            report_department_pay_gap_data = self._get_department_pay_gap_data(report_all_version_ids)
            rows = []
            for report_department, pay_gap_data in report_department_pay_gap_data.items():
                rows.append({
                    'name': report_department.name,
                    'male_median_hourly_salary': round(pay_gap_data['male_median_hourly_salary'], 2),
                    'female_median_hourly_salary': round(pay_gap_data['female_median_hourly_salary'], 2),
                    'pay_gap_percentage': round(pay_gap_data['pay_gap_percentage'], 2),
                })
            department_all_employees_pay_gap_table = request.env['ir.qweb']._render('esg_csrd_hr.esg_csrd_hr_report_department_pay_gap_table', {
                'rows': rows,
            })
            html_template_variables['{{ department_all_employees_pay_gap_table }}'] = department_all_employees_pay_gap_table

        # Data for Table: Contract Type Pay Gap (Employees + Non-Employees)
        # Reporting Year
        if report_all_version_ids and esg_report.report_type == 'csrd':
            report_contract_pay_gap_data = self._get_contract_type_pay_gap_data(report_all_version_ids)
            rows = []
            for contract_type, pay_gap_data in report_contract_pay_gap_data.items():
                rows.append({
                    'name': contract_type.name,
                    'male_median_hourly_salary': round(pay_gap_data['male_median_hourly_salary'], 2),
                    'female_median_hourly_salary': round(pay_gap_data['female_median_hourly_salary'], 2),
                    'pay_gap_percentage': round(pay_gap_data['pay_gap_percentage'], 2),
                })
            contract_type_all_employees_pay_gap_table = request.env['ir.qweb']._render('esg_csrd_hr.esg_csrd_hr_report_contract_type_pay_gap_table', {
                'rows': rows,
            })
            html_template_variables['{{ contract_type_all_employees_pay_gap_table }}'] = contract_type_all_employees_pay_gap_table

        # Data for Table: Country Pay Gap (Employees + Non-Employees)
        # Reporting Year
        if report_all_version_ids and esg_report.report_type == 'csrd':
            report_country_pay_gap_data = self._get_country_pay_gap_data(report_all_version_ids)
            rows = []
            for country, pay_gap_data in report_country_pay_gap_data.items():
                rows.append({
                    'name': country.name,
                    'male_median_hourly_salary': round(pay_gap_data['male_median_hourly_salary'], 2),
                    'female_median_hourly_salary': round(pay_gap_data['female_median_hourly_salary'], 2),
                    'pay_gap_percentage': round(pay_gap_data['pay_gap_percentage'], 2),
                })
            country_all_employees_pay_gap_table = request.env['ir.qweb']._render('esg_csrd_hr.esg_csrd_hr_report_country_pay_gap_table', {
                'rows': rows,
            })
            html_template_variables['{{ country_all_employees_pay_gap_table }}'] = country_all_employees_pay_gap_table

        # Gender Ratio at Management Level (Employees + Non-Employees)
        # Reporting Year
        if report_all_version_ids and esg_report.report_type != 'csrd':
            report_gender_management_data = self._get_gender_management_data(report_all_version_ids)
            rows = []
            for data in report_gender_management_data:
                rows.append({
                    'level': data['level'],
                    'female': data['female'],
                    'male': data['male'],
                    'other': data['other'],
                    'ratio': data['ratio'],
                })
            management_level_gender_table = request.env['ir.qweb']._render('esg_csrd_hr.esg_csrd_hr_report_management_level_gender_table', {
                'rows': rows,
            })
            html_template_variables['{{ management_level_gender_table }}'] = management_level_gender_table

        return html_template_variables
