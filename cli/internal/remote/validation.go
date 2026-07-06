package remote

import (
	"fmt"
	"net/url"
	"strings"
)

func NormalizeUrl(Url string) (string, error) {
	trimmedUrl := strings.TrimSpace(Url)
	if trimmedUrl == "" {
		return "", nil
	}

	if !strings.Contains(trimmedUrl, "://") {
		trimmedUrl = "http://" + trimmedUrl
	}

	parsedUrl, err := url.Parse(trimmedUrl)
	if err != nil {
		return "", err
	}

	if parsedUrl.Scheme != "http" && parsedUrl.Scheme != "https" {
		return "", fmt.Errorf("invalid scheme: %s", parsedUrl.Scheme)
	}

	return parsedUrl.String(), nil
}
