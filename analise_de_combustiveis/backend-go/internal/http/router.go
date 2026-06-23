package http

import (
	nethttp "net/http"

	"fuel-analytics-api/internal/domain"
	"fuel-analytics-api/internal/service"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
)

func NewRouter(repo domain.Repository, insights *service.InsightsService, mistralModel string) nethttp.Handler {
	handler := &Handler{repo: repo, insights: insights, mistralModel: mistralModel}
	r := chi.NewRouter()
	r.Use(middleware.RequestID)
	r.Use(middleware.RealIP)
	r.Use(middleware.Logger)
	r.Use(middleware.Recoverer)
	r.Use(cors)

	r.Get("/health", handler.Health)
	r.Route("/api/v1", func(r chi.Router) {
		r.Get("/fuels", handler.Fuels)
		r.Get("/overview", handler.Overview)
		r.Get("/history", handler.History)
		r.Get("/cities", handler.Cities)
		r.Get("/forecast", handler.Forecast)
		r.Get("/compare", handler.Compare)
		r.Get("/map", handler.Map)
		r.Get("/market", handler.Market)
		r.Get("/explorer", handler.Explorer)
		r.Get("/insights", handler.Insights)
		r.Get("/ranking", handler.Ranking)
		r.Get("/trends", handler.Trends)
		r.Get("/stats", handler.Stats)
	})
	return r
}

func cors(next nethttp.Handler) nethttp.Handler {
	return nethttp.HandlerFunc(func(w nethttp.ResponseWriter, r *nethttp.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Mistral-Key")
		w.Header().Set("Access-Control-Allow-Methods", "GET, OPTIONS")
		if r.Method == nethttp.MethodOptions {
			w.WriteHeader(nethttp.StatusNoContent)
			return
		}
		next.ServeHTTP(w, r)
	})
}
