package news

import "regexp"

var htmlTagPattern = regexp.MustCompile(`<[^>]+>`)
