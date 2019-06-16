import scrapy
from slugify import slugify


class FifaSpider(scrapy.Spider):
    name = "fifastats"

    # TODO - run this for extended period of time to get all players
    def start_requests(self):
        urls_all_top = [
            "https://www.fifaindex.com/players/top/fifa19",
            "https://www.fifaindex.com/players/top/fifa18/",
            "https://www.fifaindex.com/players/top/fifa17/",
            "https://www.fifaindex.com/players/top/fifa16/",
            "https://www.fifaindex.com/players/top/fifa15/",
            "https://www.fifaindex.com/players/top/fifa14/",
            "https://www.fifaindex.com/players/top/fifa13/",
        ] # use this for top100 players
        urls = [
            "https://www.fifaindex.com/players/fifa19",
            "https://www.fifaindex.com/players/fifa18/",
            "https://www.fifaindex.com/players/fifa17/",
            "https://www.fifaindex.com/players/fifa16/",
            "https://www.fifaindex.com/players/fifa15/",
            "https://www.fifaindex.com/players/fifa14/",
            "https://www.fifaindex.com/players/fifa13/",
        ]
        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        for player_row in response.css("tr"):
            link = player_row.css("figure.player a::attr(href)").get()
            if link:
                if "/player/" in link:
                    # extract team
                    team = player_row.css("a.link-team")
                    if team:
                        # only add if player has a team
                        team_name = team.attrib["title"]
                        request = response.follow(link, callback=self.parse_player)
                        # pass additional parameter for the player
                        request.meta["team"] = team_name
                        yield request

        for page_link in response.css(".pagination a.page-link"):
            text = page_link.css("::text").get()
            next = page_link.attrib["href"]
            if "Next" in text:
                print("Next page:", next)
                yield response.follow(next, callback=self.parse)

    @staticmethod
    def parse_player(response):
        name = response.css("img.player").attrib["title"]
        
        team = response.meta["team"]
        if not team:
            # gives the title of the first occurence
            team = (
                response.css("div.team")
                .css("a.link-team")
                .attrib["title"]
            )

        number = (
            response.css("div.team")    # multiple results when multiple teams !
            .css("span.float-right::text")
            .get()
        )

        position = (
            response.css("div.team")    # multiple results when multiple teams !
            .css("a.link-position")
            .attrib["title"]
        )

        rating = response.css(".card-header span.rating::text").get() # first: total, second: potential

        nationality = response.css("a.link-nation").attrib["title"]

        yield {
            "name": slugify(name),
            "info": {
                "raw team": team,
                "team": slugify(team),
                "position": position,
                "raw name": name,
                "rating": int(rating),
                "kit number": number,
                "nationality": slugify(nationality),
                "url": response.request.url,
            },
        }


class MatchSpider(scrapy.Spider):
    name = "matchlineups"

    # TODO - want the other names - not full names

    def start_requests(self):
        urls = [
            "http://www.betstudy.com/soccer-stats/c/france/ligue-1/d/results/2017-2018/",
            "http://www.betstudy.com/soccer-stats/c/france/ligue-1/d/results/2016-2017/",
            "http://www.betstudy.com/soccer-stats/c/france/ligue-1/d/results/2015-2016/",
            "http://www.betstudy.com/soccer-stats/c/france/ligue-1/d/results/2014-2015/",
            "http://www.betstudy.com/soccer-stats/c/france/ligue-1/d/results/2013-2014/",
        ]
        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse_fixtures_page)

    def parse_fixtures_page(self, response):
        for info_button in response.css("ul.action-list").css("a::attr(href)"):
            url = response.urljoin(info_button.extract())
            yield scrapy.Request(url, callback=self.parse_match_page)

    def parse_match_page(self, response):

        home_team, away_team = response.css("div.player h2 a::text").extract()

        date = response.css("em.date").css("span.timestamp::text").extract_first()

        url = response.request.url

        match_number = response.request.url.split("-")[-1].split("/")[0]

        home_goals, away_goals = (
            response.css("div.info strong.score::text").extract_first().split("-")
        )

        for table in response.css("div.table-holder"):
            if table.css("h2::text").extract_first() == "Lineups and subsitutes":
                lineups = table

        home_lineup_css = lineups.css("table.info-table")[0]
        away_lineup_css = lineups.css("table.info-table")[1]

        home_lineup_raw = [
            slugify(x)
            for x in home_lineup_css.css("tr td.left-align")
            .css("a::attr(title)")
            .extract()
        ]
        away_lineup_raw = [
            slugify(x)
            for x in away_lineup_css.css("tr td.left-align")
            .css("a::attr(title)")
            .extract()
        ]

        home_lineup = [
            slugify(x)
            for x in home_lineup_css.css("tr td.left-align").css("a::text").extract()
        ]
        away_lineup = [
            slugify(x)
            for x in away_lineup_css.css("tr td.left-align").css("a::text").extract()
        ]

        home_lineup_number = [
            int(x) for x in home_lineup_css.css("tr td.size23 strong::text").extract()
        ]
        away_lineup_number = [
            int(x) for x in away_lineup_css.css("tr td.size23 strong::text").extract()
        ]

        home_lineup_nationality = [
            slugify(x)
            for x in home_lineup_css.css("tr td.left-align")
            .css("img.flag-ico::attr(alt)")
            .extract()
        ]
        away_lineup_nationality = [
            slugify(x)
            for x in away_lineup_css.css("tr td.left-align")
            .css("img.flag-ico::attr(alt)")
            .extract()
        ]

        yield {
            "match number": int(match_number),
            "info": {
                "date": date,
                "home team": slugify(home_team),
                "away team": slugify(away_team),
                "home goals": int(home_goals),
                "away goals": int(away_goals),
                "home lineup raw names": home_lineup_raw,
                "away lineup raw names": away_lineup_raw,
                "home lineup names": home_lineup,
                "away lineup names": away_lineup,
                "home lineup numbers": home_lineup_number,
                "away lineup numbers": away_lineup_number,
                "home lineup nationalities": home_lineup_nationality,
                "away lineup nationalities": away_lineup_nationality,
                "url": url,
            },
        }


class FifaIndexTeamScraper(scrapy.Spider):
    name = "fifa-index-team"

    # TODO - run this for extended period of time to get all players

    def start_requests(self):
        urls = [
            "https://www.fifaindex.com/teams/",
            "https://www.fifaindex.com/teams/fifa17_173/",
            "https://www.fifaindex.com/teams/fifa16_73/",
            "https://www.fifaindex.com/teams/fifa15_14/",
            "https://www.fifaindex.com/teams/fifa14_13/",
        ]
        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        links = [a.extract() for a in response.css("td a::attr(href)")]
        for link in links:
            if "/team/" in link:
                url = response.urljoin(link)
                yield scrapy.Request(url, callback=self.parse_team)

        next_page = response.css("li.next a::attr(href)").extract_first()
        if next_page is not None and int(next_page.split("/")[-2]) < 10:
            next_page = response.urljoin(next_page)
            yield scrapy.Request(next_page, callback=self.parse)

    @staticmethod
    def parse_team(response):
        team = slugify(response.css(".media-heading::text").extract_first())

        for i in range(1, len(response.css('tr'))):
            name_css = (
                ".table > "
                "tbody:nth-child(2) > "
                "tr:nth-child({}) > "
                "td:nth-child(6) > "
                "a:nth-child(1)::attr(title)"
            )
            name = slugify(response.css(name_css.format(i)).extract_first())

            number_css = (
                ".table > " "tbody:nth-child(2) > " "tr:nth-child({}) > " "td:nth-child(1)::t" "ext"
            )
            number = int(response.css(number_css.format(i)).extract_first())

            nationality_css = (
                ".table > "
                "tbody:nth-child(2) > "
                "tr:nth-child({}) > "
                "td:nth-child(4) > "
                "a:nth-child(1) > img:nth-child(1)::attr(title)"
            )
            nationality = slugify(
                response.css(nationality_css.format(i)).extract_first())

            position_css = (
                ".table > "
                "tbody:nth-child(2) > "
                "tr:nth-child({}) > "
                "td:nth-child(7) > "
                "a:nth-child(1) > span:nth-child(1)::text"
            )
            position = response.css(position_css.format(i)).extract_first()

            rating_css = (
                "table > t"
                "body:nth-child(2) > t"
                "r:nth-child({}) > t"
                "d:nth-child(5) > s"
                "pan:nth-child(1)::text"
            )
            rating = response.css(rating_css.format(i)).extract_first()

            yield {
                "name": slugify(name),
                "team": team,
                "position": position,
                "rating": int(rating),
                "number": number,
                "nationality": nationality,
                "url": response.request.url,
            }


class FixturesSpider(scrapy.Spider):
    name = "fixtures"

    # TODO - want the other names - not full names

    def start_requests(self):
        urls = [
            "http://www.betstudy.com/soccer-stats/c/england/premier-league/d/fixtures/"
        ]
        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse_fixtures)

    @staticmethod
    def parse_fixtures(response):
        for fixture in response.css("tr")[1:]:
            home_team = fixture.css("td.right-align a::text").extract_first()
            away_team = fixture.css("td.left-align a::text").extract_first()
            date = fixture.css("td::text").extract_first()
            yield {
                "date": date,
                "home team": slugify(home_team),
                "away team": slugify(away_team),
                "url": response.request.url,
            }
