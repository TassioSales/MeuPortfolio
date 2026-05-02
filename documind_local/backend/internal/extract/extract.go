package extract

import (
	"archive/zip"
	"bytes"
	"encoding/xml"
	"errors"
	"io"
	"mime/multipart"
	"os"
	"path/filepath"
	"regexp"
	"strings"
)

var htmlTagPattern = regexp.MustCompile(`<[^>]+>`)

func Text(file multipart.File, filename string) (string, error) {
	content, err := io.ReadAll(io.LimitReader(file, 8_000_000))
	if err != nil {
		return "", err
	}

	ext := strings.ToLower(filepath.Ext(filename))
	switch ext {
	case ".txt", ".md", ".csv", ".json", ".log":
		return cleanPlain(string(content)), nil
	case ".html", ".htm":
		return cleanPlain(htmlTagPattern.ReplaceAllString(string(content), " ")), nil
	case ".pdf":
		return extractPDFBytes(content)
	case ".docx":
		return extractDocx(content)
	case ".xlsx":
		return extractXlsx(content)
	default:
		return "", errors.New("formato ainda nao suportado para extracao de texto")
	}
}

func TextFromPath(path, filename string) (string, error) {
	ext := strings.ToLower(filepath.Ext(filename))
	if ext == ".pdf" {
		if text, err := extractPDFWithPython(path); err == nil {
			return cleanPlain(text), nil
		}
	}

	file, err := os.Open(path)
	if err != nil {
		return "", err
	}
	defer file.Close()
	return Text(file, filename)
}

func extractDocx(content []byte) (string, error) {
	reader, err := zip.NewReader(bytes.NewReader(content), int64(len(content)))
	if err != nil {
		return "", err
	}

	for _, file := range reader.File {
		if file.Name == "word/document.xml" {
			return collectXMLText(file)
		}
	}
	return "", errors.New("document.xml nao encontrado")
}

func extractXlsx(content []byte) (string, error) {
	reader, err := zip.NewReader(bytes.NewReader(content), int64(len(content)))
	if err != nil {
		return "", err
	}

	parts := []string{}
	for _, file := range reader.File {
		if strings.HasPrefix(file.Name, "xl/worksheets/") || file.Name == "xl/sharedStrings.xml" {
			text, err := collectXMLText(file)
			if err == nil && text != "" {
				parts = append(parts, text)
			}
		}
	}
	if len(parts) == 0 {
		return "", errors.New("planilha sem texto extraivel")
	}
	return cleanPlain(strings.Join(parts, " ")), nil
}

func collectXMLText(file *zip.File) (string, error) {
	handle, err := file.Open()
	if err != nil {
		return "", err
	}
	defer handle.Close()

	decoder := xml.NewDecoder(handle)
	parts := []string{}
	for {
		token, err := decoder.Token()
		if err == io.EOF {
			break
		}
		if err != nil {
			return "", err
		}
		if chars, ok := token.(xml.CharData); ok {
			value := strings.TrimSpace(string(chars))
			if value != "" {
				parts = append(parts, value)
			}
		}
	}
	return cleanPlain(strings.Join(parts, " ")), nil
}

func cleanPlain(value string) string {
	return strings.Join(strings.Fields(value), " ")
}
