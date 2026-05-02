package extract

import (
	"bytes"
	"compress/flate"
	"errors"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"time"
)

var (
	pdfStreamPattern       = regexp.MustCompile(`(?s)<<(.*?)>>\s*stream\r?\n(.*?)\r?\nendstream`)
	pdfLiteralString       = regexp.MustCompile(`\((?:\\.|[^\\)])*\)`)
	pdfHexString           = regexp.MustCompile(`<([0-9A-Fa-f\s]{4,})>`)
	pdfTextArrayOrOperator = regexp.MustCompile(`(?s)(\[(?:.|\n)*?\]|\((?:\\.|[^\\)])*\))\s*T[Jj]`)
)

func extractPDFWithPython(path string) (string, error) {
	script := filepath.Clean("tools/pdf_extract.py")
	commands := [][]string{
		{filepath.Clean(".venv/Scripts/python.exe"), script, path},
		{"py", script, path},
		{"python", script, path},
		{"python3", script, path},
	}

	var lastErr error
	for _, parts := range commands {
		if _, err := os.Stat(parts[0]); strings.Contains(parts[0], ".venv") && err != nil {
			continue
		}
		cmd := exec.Command(parts[0], parts[1:]...)
		cmd.Dir = filepath.Clean(".")
		timer := time.AfterFunc(45*time.Second, func() {
			_ = cmd.Process.Kill()
		})
		output, err := cmd.Output()
		timer.Stop()
		if err == nil && len(output) > 80 {
			return string(output), nil
		}
		lastErr = err
	}
	if lastErr == nil {
		lastErr = errors.New("python nao encontrado ou nenhuma biblioteca de PDF instalada")
	}
	return "", lastErr
}

func extractPDFBytes(content []byte) (string, error) {
	matches := pdfStreamPattern.FindAllSubmatch(content, -1)
	parts := []string{}

	for _, match := range matches {
		dict := string(match[1])
		stream := bytes.Trim(match[2], "\r\n")
		if strings.Contains(dict, "/FlateDecode") {
			inflated, err := inflate(stream)
			if err == nil {
				stream = inflated
			}
		}
		if !strings.Contains(dict, "/Length") {
			continue
		}
		text := extractPDFTextFromStream(stream)
		if text != "" {
			parts = append(parts, text)
		}
	}

	result := cleanPlain(strings.Join(parts, " "))
	if len(result) < 40 {
		return "", errors.New("pdf sem texto extraivel; pode ser escaneado ou usar codificacao nao suportada")
	}
	return result, nil
}

func inflate(content []byte) ([]byte, error) {
	reader := flate.NewReader(bytes.NewReader(content))
	defer reader.Close()
	return io.ReadAll(reader)
}

func extractPDFTextFromStream(stream []byte) string {
	raw := string(stream)
	fragments := []string{}

	for _, block := range pdfTextArrayOrOperator.FindAllString(raw, -1) {
		for _, literal := range pdfLiteralString.FindAllString(block, -1) {
			fragments = append(fragments, decodePDFLiteral(literal))
		}
		for _, hexMatch := range pdfHexString.FindAllStringSubmatch(block, -1) {
			fragments = append(fragments, decodePDFHex(hexMatch[1]))
		}
	}

	if len(fragments) == 0 {
		for _, literal := range pdfLiteralString.FindAllString(raw, -1) {
			decoded := decodePDFLiteral(literal)
			if len(decoded) > 2 {
				fragments = append(fragments, decoded)
			}
		}
	}

	return cleanPlain(strings.Join(fragments, " "))
}

func decodePDFLiteral(value string) string {
	value = strings.TrimPrefix(strings.TrimSuffix(value, ")"), "(")
	var builder strings.Builder
	for i := 0; i < len(value); i++ {
		char := value[i]
		if char != '\\' || i == len(value)-1 {
			builder.WriteByte(char)
			continue
		}
		i++
		switch value[i] {
		case 'n':
			builder.WriteByte(' ')
		case 'r':
			builder.WriteByte(' ')
		case 't':
			builder.WriteByte(' ')
		case 'b', 'f':
			builder.WriteByte(' ')
		case '\\', '(', ')':
			builder.WriteByte(value[i])
		default:
			if value[i] >= '0' && value[i] <= '7' {
				end := i + 1
				for end < len(value) && end < i+3 && value[end] >= '0' && value[end] <= '7' {
					end++
				}
				if parsed, err := strconv.ParseInt(value[i:end], 8, 32); err == nil {
					builder.WriteRune(rune(parsed))
				}
				i = end - 1
			} else {
				builder.WriteByte(value[i])
			}
		}
	}
	return builder.String()
}

func decodePDFHex(value string) string {
	value = strings.Join(strings.Fields(value), "")
	if len(value)%2 == 1 {
		value += "0"
	}

	bytesOut := make([]byte, 0, len(value)/2)
	for i := 0; i < len(value); i += 2 {
		parsed, err := strconv.ParseUint(value[i:i+2], 16, 8)
		if err == nil && parsed != 0 {
			bytesOut = append(bytesOut, byte(parsed))
		}
	}

	if len(bytesOut) >= 2 && bytesOut[0] == 0xfe && bytesOut[1] == 0xff {
		runes := []rune{}
		for i := 2; i+1 < len(bytesOut); i += 2 {
			runes = append(runes, rune(uint16(bytesOut[i])<<8|uint16(bytesOut[i+1])))
		}
		return string(runes)
	}

	return string(bytesOut)
}
